import json  # 👉 for parsing JSON if needed
import stripe  # 👉 stripe api client
from django.utils import timezone  # 👉 used for timestamps
from datetime import timedelta
from django.conf import settings  # 👉 to access environment config like stripe keys
from django.contrib.auth import get_user_model  # 👉 for dynamic access to custom user model
from dateutil.relativedelta import relativedelta  # 👉 used to calculate future billing dates

from rest_framework.response import Response  # 👉 used to return API responses
from rest_framework.decorators import api_view, permission_classes  # 👉 decorator for function-based API views
from rest_framework.permissions import AllowAny  # 👉 allows non-authenticated access to this route
from rest_framework import status  # 👉 standard HTTP status codes
from rest_framework_simplejwt.tokens import RefreshToken  # 👉 generates JWT tokens for login response

from users.admin_area.models import Plan, Profile, PendingSignup, AdminIdentity, EventTracker 

from users.admin_area.utils.profile_creator import log_profile_event  # 👉 creates billing profile snapshot

stripe.api_key = settings.STRIPE_SECRET_KEY  # 👉 initializes stripe with secret key
User = get_user_model()  # 👉 loads the active custom user model

@api_view(['POST'])  # 👉 allows only POST requests
@permission_classes([AllowAny])  # 👉 open to unauthenticated users (used for admin registration after Stripe checkout)
def register(request):
    data = request.data
    email = data.get('email')
    password = data.get('password')
    token = data.get('token')

    if not all([email, password, token]):
        return Response({'error': 'Missing fields'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        pending = PendingSignup.objects.get(token=token)
    except PendingSignup.DoesNotExist:
        return Response({'error': 'Invalid or expired token'}, status=status.HTTP_404_NOT_FOUND)

    session_id = pending.session_id

    try:
        checkout_session = stripe.checkout.Session.retrieve(session_id, expand=['customer', 'setup_intent'])  # 👉 fetch stripe session
    except stripe.error.StripeError as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
    stripe_transaction_id = pending.stripe_transaction_id
    customer_obj = checkout_session.get("customer")
    customer_id = customer_obj["id"] if isinstance(customer_obj, dict) else customer_obj
    customer_email = checkout_session.get("customer_email") or customer_obj.get("email")

    raw_plan_name = checkout_session.get('metadata', {}).get('plan_name')
    actual_plan_name = 'adminMonthly' if raw_plan_name == 'adminTrial' else raw_plan_name
    is_trial = raw_plan_name == 'adminTrial'

    try:
        plan = Plan.objects.get(name=actual_plan_name)
    except Plan.DoesNotExist:
        return Response({'error': 'Plan not found'}, status=status.HTTP_404_NOT_FOUND)

    plan_mapping = {
        'adminMonthly': 'admin_monthly',
        'adminQuarterly': 'admin_quarterly',
        'adminAnnual': 'admin_annual',
    }
    subscription_status = plan_mapping.get(actual_plan_name, 'admin_monthly')

    if User.objects.filter(username=email).exists():
        return Response({'error': 'User already exists'}, status=status.HTTP_400_BAD_REQUEST)

    # 👉 create user account
    user = User.objects.create_user(username=email, email=email, password=password)
    user.role = 'admin'
    user.is_staff = True
    user.subscription_status = subscription_status
    user.save()

    now = timezone.now()

    # 👉 Log event in EventTracker
    admin_identity = AdminIdentity.objects.filter(admin_email=email).first()
    if admin_identity:
        EventTracker.objects.create(
            admin=admin_identity,
            event_type="registration_success",
            timestamp=timezone.now()
        )
    else:
        print(f"⚠️ No AdminIdentity found for {email}. Cannot log EventTracker.")



    # Set trial_start and subscription_start based on whether this is a trial
    if is_trial:
        trial_start = now
        subscription_start = None  # leave null for trial profiles
        subscription_end = now + relativedelta(days=14)
    else:
        trial_start = None
        subscription_start = now

        if subscription_status == 'admin_monthly':
            subscription_end = now + relativedelta(months=1)
        elif subscription_status == 'admin_quarterly':
            subscription_end = now + relativedelta(months=3)
        elif subscription_status == 'admin_annual':
            subscription_end = now + relativedelta(months=12)
        else:
            subscription_end = None


    # 👉 create initial billing profile snapshot
    next_billing_date = timezone.now() + timedelta(days=14)
    log_profile_event(
            user=user,
            plan=plan,
            stripe_transaction_id=stripe_transaction_id,
            is_trial=is_trial,
            trial_start=trial_start,
            subscription_start=subscription_start,
            subscription_end=subscription_end,
            next_billing=next_billing_date
        )


    # 👉 attach default payment method if setup intent was used
    if checkout_session.mode == 'setup':
        setup_intent = checkout_session.get('setup_intent')
        if setup_intent and setup_intent.get('payment_method'):
            try:
                stripe.PaymentMethod.attach(setup_intent['payment_method'], customer=customer_id)
                stripe.Customer.modify(customer_id, invoice_settings={
                    'default_payment_method': setup_intent['payment_method']
                })
            except stripe.error.StripeError as e:
                return Response({'error': f'Failed to attach payment method: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

    pending.delete()  # 👉 remove used token to prevent reuse

    # 👉 generate jwt token for login response
    refresh = RefreshToken.for_user(user)
    refresh['email'] = user.email
    refresh['role'] = user.role
    refresh['subscription_status'] = user.subscription_status


    # 👉 generate jwt token for login response
    refresh = RefreshToken.for_user(user)


    return Response({
        'success': True,
        'message': f'Admin account created with {subscription_status} plan',
        'refresh': str(refresh),
        'access': str(refresh.access_token),
        'user_id': user.id,
        'email': user.email,
        'role': user.role,
        'subscription_status': user.subscription_status,
    }, status=status.HTTP_201_CREATED)


# 👉 summary:
# handles the full post-stripe registration flow for admin users.
# verifies the pending token, pulls stripe session details, creates the user,
# logs the subscription event, creates a profile, and returns a jwt login token.
# designed for seamless onboarding after checkout and supports trial and paid plans.

