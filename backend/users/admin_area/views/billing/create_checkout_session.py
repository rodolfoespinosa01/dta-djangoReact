import stripe
import json

from django.conf import settings
from django.utils.crypto import get_random_string
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from core.models import CustomUser
from users.admin_area.models import Plan, PendingSignup, PreCheckoutEmail

stripe.api_key = settings.STRIPE_SECRET_KEY

@api_view(['POST'])
@permission_classes([AllowAny])
def create_checkout_session(request):
    try:
        data = request.data
        plan_name = data.get('plan_name')
        email = data.get('email')
        # Save for tracking unpaid email attempts
        PreCheckoutEmail.objects.get_or_create(email=email)

        if not plan_name or not email:
            return Response({'error': 'Missing plan or email'}, status=status.HTTP_400_BAD_REQUEST)

        # 🔒 Block if user already exists (active, inactive, canceled, etc.)
        existing_user = CustomUser.objects.filter(email=email).first()
        if existing_user:
            return Response({
                'error': 'This email is already associated with an account. Please log in or reactivate your plan.'
            }, status=status.HTTP_403_FORBIDDEN)

        # 🔒 Block if there is an unused PendingSignup
        if PendingSignup.objects.filter(email=email, is_used=False).exists():
            return Response({
                'error': 'A registration link has already been generated for this email. Please complete your registration or wait for it to expire.'
            }, status=status.HTTP_403_FORBIDDEN)

        # Normalize plan name for trial
        actual_plan_name = 'adminMonthly' if plan_name == 'adminTrial' else plan_name

        # Get Plan from DB
        plan = Plan.objects.get(name=actual_plan_name)

        # Create Stripe Customer
        customer = stripe.Customer.create(email=email)

        # Create Stripe Checkout Session
        session = stripe.checkout.Session.create(
            mode='subscription',
            payment_method_types=['card'],
            customer=customer.id,
            line_items=[{
                'price': plan.stripe_price_id,
                'quantity': 1,
            }],
            metadata={
                'plan_name': plan_name  # Use original input (even if it's adminTrial)
            },
            success_url='http://localhost:3000/admin_thank_you?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='http://localhost:3000/admin_plans',
        )

        # Save pending signup (actual registration happens later)
        PendingSignup.objects.create(
            email=email,
            session_id=session.id,
            subscription_id=session.subscription,
            is_used=False,
            token=get_random_string(32),
            plan=plan_name,
        )

        return Response({'url': session.url}, status=status.HTTP_200_OK)

    except Plan.DoesNotExist:
        return Response({'error': 'Plan not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print("❌ Error creating checkout session:", str(e))
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
