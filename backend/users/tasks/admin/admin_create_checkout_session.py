import stripe
import json

from django.conf import settings
from django.utils.crypto import get_random_string
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from users.models.custom_user import CustomUser
from adminplans.models import AdminPlan, AdminPendingSignup

stripe.api_key = settings.STRIPE_SECRET_KEY

@api_view(['POST'])
@permission_classes([AllowAny])
def admin_create_checkout_session(request):
    try:
        data = request.data
        plan_name = data.get('plan_name')
        email = data.get('email')

        if not plan_name or not email:
            return Response({'error': 'Missing plan or email'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if user already exists
        existing_user = CustomUser.objects.filter(email=email).first()
        if existing_user:
            if existing_user.subscription_status in ['admin_trial', 'admin_monthly', 'admin_quarterly', 'admin_annual', 'admin_inactive']:
                return Response({
                    'error': 'This email is already associated with an account. Please log in to manage or upgrade your plan.'
                }, status=status.HTTP_403_FORBIDDEN)

        # Prevent free trial abuse
        if plan_name == 'adminTrial':
            if existing_user and hasattr(existing_user, 'admin_profile'):
                if existing_user.admin_profile.trial_start_date:
                    return Response({
                        'error': 'This email has already used the free trial. Please choose a paid plan.'
                    }, status=status.HTTP_403_FORBIDDEN)

        # Prevent pending signup abuse
        if AdminPendingSignup.objects.filter(email=email, is_used=False).exists():
            return Response({
                'error': 'A registration link has already been generated for this email. Please complete your registration or wait for it to expire.'
            }, status=status.HTTP_403_FORBIDDEN)

        # Normalize plan (adminTrial still uses adminMonthly price ID)
        actual_plan_name = 'adminMonthly' if plan_name == 'adminTrial' else plan_name

        # Lookup Stripe plan
        plan = AdminPlan.objects.get(name=actual_plan_name)
        customer = stripe.Customer.create(email=email)

        # Create Stripe session (subscription mode for all plans)
        session = stripe.checkout.Session.create(
            mode='subscription',
            payment_method_types=['card'],
            customer=customer.id,
            line_items=[{
                'price': plan.stripe_price_id,
                'quantity': 1,
            }],
            metadata={
                'plan_name': plan_name  # Keep original to detect trial in webhook
            },
            success_url='http://localhost:3000/admin_thank_you?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='http://localhost:3000/admin_plans',
        )

        return Response({'url': session.url}, status=status.HTTP_200_OK)

    except AdminPlan.DoesNotExist:
        return Response({'error': 'Plan not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print("❌ Error creating checkout session:", str(e))
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
