import stripe
import json

from django.conf import settings
from django.utils.crypto import get_random_string  # 👉 future use: unique referral or invite tokens
from django.utils import timezone  # 👉 for potential future timestamp tracking
from users.admin_area.models import AccountHistory

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from core.models import CustomUser
from users.admin_area.models import Plan, PendingSignup, PreCheckoutEmail
from users.admin_area.utils import log_precheckout_event

stripe.api_key = settings.STRIPE_SECRET_KEY


@api_view(['POST'])
@permission_classes([AllowAny])
def create_checkout_session(request):
    try:
       
        data = request.data
        plan_name = data.get('plan_name')
        email = data.get('email')
        is_trial = data.get('is_trial', False)

        has_had_trial = AccountHistory.objects.filter(
            user__email=email,
            event_type__startswith='trial_'
        ).exists()

        if is_trial and has_had_trial:
            return Response({
                'error': 'You have already used a trial. Please choose a paid plan.',
                'redirect': '/admin_reactivate'
            }, status=403)

        # ✅ Basic validation
        if not plan_name or not email:
            return Response({'error': 'Missing plan or email'}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Log pre-checkout email for early lead tracking
        log_precheckout_event(email=email, plan_name=plan_name, is_trial=is_trial)

        # ❌ Block reuse if user already exists
        if CustomUser.objects.filter(email=email).exists():
            return Response({'error': 'This email is already associated with an account. Please log in.'}, status=status.HTTP_403_FORBIDDEN)

        # ❌ Prevent multiple pending signups
        if PendingSignup.objects.filter(email=email).exists():
            return Response({'error': 'A registration link has already been generated for this email.'}, status=status.HTTP_403_FORBIDDEN)



        # ✅ Determine plan and Stripe price
        plan = Plan.objects.get(name=plan_name)

        # ✅ Create a new Stripe customer
        customer = stripe.Customer.create(email=email)

        # ✅ Create the Stripe Checkout session
        session = stripe.checkout.Session.create(
            mode='subscription',
            payment_method_types=['card'],
            customer_email=email,
            line_items=[{
                'price': plan.stripe_price_id,
                'quantity': 1,
            }],
            metadata={
                'plan_name': plan_name,
                'is_trial': str(is_trial),
            },
            subscription_data={
                'trial_period_days': 14 if is_trial else None,
            },
            success_url='http://localhost:3000/admin_thank_you?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='http://localhost:3000/admin_plans',
        )

        return Response({'url': session.url}, status=status.HTTP_200_OK)

    except Plan.DoesNotExist:
        return Response({'error': 'Plan not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print("❌ Error creating checkout session:", str(e))
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



# ✅ Summary:
# This view:
# - Validates email and plan
# - Prevents duplicate user signups or multiple pending registrations
# - Creates Stripe Checkout session with correct trial or paid logic
# - Logs pre-checkout emails for attribution
# - Returns secure Stripe-hosted session URL to frontend
