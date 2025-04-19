import stripe
import json

from django.conf import settings
from django.utils.crypto import get_random_string
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from users.models import CustomUser
from adminplans.models import AdminPlan, PendingAdminSignup

stripe.api_key = settings.STRIPE_SECRET_KEY

@api_view(['POST'])
@permission_classes([AllowAny])
def create_admin_checkout_session(request):
    try:
        data = request.data
        plan_name = data.get('plan_name')
        email = data.get('email')

        if not plan_name or not email:
            return Response({'error': 'Missing plan or email'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if user already exists with an active or used plan
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

        # Prevent multiple pending signups
        if PendingAdminSignup.objects.filter(email=email, is_used=False).exists():
            return Response({
                'error': 'A registration link has already been generated for this email. Please complete your registration or wait for it to expire.'
            }, status=status.HTTP_403_FORBIDDEN)

        # Create Stripe customer and session
        plan = AdminPlan.objects.get(name=plan_name)
        customer = stripe.Customer.create(email=email)

        if plan.name == 'adminTrial':
            session = stripe.checkout.Session.create(
                mode='setup',
                payment_method_types=['card'],
                customer=customer.id,
                metadata={'plan_name': plan.name},
                success_url='http://localhost:3000/admin-thank-you?session_id={CHECKOUT_SESSION_ID}',
                cancel_url='http://localhost:3000/admin-plans',
            )
        else:
            session = stripe.checkout.Session.create(
                mode='subscription',
                payment_method_types=['card'],
                customer=customer.id,
                line_items=[{
                    'price': plan.stripe_price_id,
                    'quantity': 1,
                }],
                metadata={'plan_name': plan.name},
                success_url='http://localhost:3000/admin-thank-you?session_id={CHECKOUT_SESSION_ID}',
                cancel_url='http://localhost:3000/admin-plans',
            )

        return Response({'url': session.url}, status=status.HTTP_200_OK)

    except AdminPlan.DoesNotExist:
        return Response({'error': 'Plan not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print("❌ Error creating checkout session:", str(e))
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
