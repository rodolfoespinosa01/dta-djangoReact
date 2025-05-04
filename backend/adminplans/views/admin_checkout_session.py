import stripe
import json

from django.conf import settings
from django.utils.crypto import get_random_string
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

<<<<<<<< HEAD:backend/adminplans/views/admin_checkout_session.py
from users.models.custom_user import CustomUser
from adminplans.models import AdminPlan, AdminPendingSignup
========
from core.models import CustomUser
from users.admin_area.models import AdminPlan, AdminPendingSignup
>>>>>>>> admin-reactivation-debug:backend/users/admin_area/tasks/admin_create_checkout_session.py

# Set Stripe secret key
stripe.api_key = settings.STRIPE_SECRET_KEY

@api_view(['POST'])
<<<<<<<< HEAD:backend/adminplans/views/admin_checkout_session.py
@permission_classes([AllowAny])  # Public access (no login required)
def admin_checkout_session(request):
========
@permission_classes([AllowAny])
def admin_create_checkout_session(request):
>>>>>>>> admin-reactivation-debug:backend/users/admin_area/tasks/admin_create_checkout_session.py
    try:
        data = request.data
        plan_name = data.get('plan_name')
        email = data.get('email')

        # Validate required fields
        if not plan_name or not email:
            return Response({'error': 'Missing plan or email'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if the user already exists (used for upgrade/reactivation validation)
        existing_user = CustomUser.objects.filter(email=email).first()
        if existing_user:
            if existing_user.subscription_status in [
                'admin_trial', 'admin_monthly', 'admin_quarterly', 'admin_annual', 'admin_inactive'
            ]:
                return Response({
                    'error': 'This email is already associated with an account. Please log in to manage or upgrade your plan.'
                }, status=status.HTTP_403_FORBIDDEN)

        # Prevent trial abuse: reject if user already has a trial start date
        if plan_name == 'adminTrial':
            if existing_user and hasattr(existing_user, 'admin_profile'):
                if existing_user.admin_profile.trial_start_date:
                    return Response({
                        'error': 'This email has already used the free trial. Please choose a paid plan.'
                    }, status=status.HTTP_403_FORBIDDEN)

<<<<<<<< HEAD:backend/adminplans/views/admin_checkout_session.py
        # Prevent multiple pending registrations
========
        # Prevent pending signup abuse
>>>>>>>> admin-reactivation-debug:backend/users/admin_area/tasks/admin_create_checkout_session.py
        if AdminPendingSignup.objects.filter(email=email, is_used=False).exists():
            return Response({
                'error': 'A registration link has already been generated for this email. Please complete your registration or wait for it to expire.'
            }, status=status.HTTP_403_FORBIDDEN)

        # Normalize trial → monthly (Stripe price ID for adminTrial uses monthly under the hood)
        actual_plan_name = 'adminMonthly' if plan_name == 'adminTrial' else plan_name

        # Get corresponding plan info from DB
        plan = AdminPlan.objects.get(name=actual_plan_name)

        # Create Stripe customer (linked to email)
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
                'plan_name': plan_name  # Use raw plan name to detect trials in webhook
            },
            success_url='http://localhost:3000/admin_thank_you?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='http://localhost:3000/admin_plans',
        )

        # Return Stripe Checkout URL to frontend
        return Response({'url': session.url}, status=status.HTTP_200_OK)

    except AdminPlan.DoesNotExist:
        return Response({'error': 'Plan not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        # Catch-all error handling
        print("❌ Error creating checkout session:", str(e))
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
