import json
import stripe
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from dateutil.relativedelta import relativedelta

from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from users.admin_area.models import Plan, Profile, PendingSignup

from users.admin_area.utils.account_history import log_account_event

stripe.api_key = settings.STRIPE_SECRET_KEY
User = get_user_model()

@api_view(['POST'])
@permission_classes([AllowAny])
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
    subscription_id = pending.subscription_id

    try:
        checkout_session = stripe.checkout.Session.retrieve(session_id, expand=['customer', 'setup_intent'])
    except stripe.error.StripeError as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    customer_obj = checkout_session.get("customer")
    customer_id = customer_obj["id"] if isinstance(customer_obj, dict) else customer_obj
    customer_email = checkout_session.get("customer_email") or customer_obj.get("email")

    # Normalize adminTrial to adminMonthly internally
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

    user = User.objects.create_user(username=email, email=email, password=password)
    user.role = 'admin'
    user.is_staff = True
    user.subscription_status = subscription_status
    user.save()

    # AdminProfile creation
    now = timezone.now()
    profile_data = {
        'stripe_customer_id': customer_id,
        'stripe_subscription_id': subscription_id,
        'subscription_started_at': now,
    }

    if is_trial:
        profile_data['trial_start_date'] = now
        profile_data['next_billing_date'] = now + relativedelta(days=14)
    elif subscription_status == 'monthly':
        profile_data['next_billing_date'] = now + relativedelta(months=1)
    elif subscription_status == 'quarterly':
        profile_data['next_billing_date'] = now + relativedelta(months=3)
    elif subscription_status == 'annual':
        profile_data['next_billing_date'] = now + relativedelta(months=12)

    profile, created = Profile.objects.get_or_create(user=user, defaults=profile_data)

    log_account_event(
        user=user,
        event_type='signup',
        plan_name=actual_plan_name,
        stripe_subscription_id=subscription_id,
        subscription_start=profile.subscription_started_at,
        subscription_end=profile.next_billing_date
    )

    # Handle setup intent mode if needed
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

    # Cleanup token so it's one-time use only
    pending.delete()

    # JWT response
    refresh = RefreshToken.for_user(user)
    refresh['email'] = user.email
    refresh['role'] = user.role
    refresh['subscription_status'] = user.subscription_status

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
