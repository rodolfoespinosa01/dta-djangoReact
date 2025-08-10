import json
import stripe
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from dateutil.relativedelta import relativedelta

from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from users.admin_area.models import Plan, Profile, PendingSignup, AdminIdentity, EventTracker
from users.admin_area.utils.log_profile_event import log_profile_event

stripe.api_key = settings.STRIPE_SECRET_KEY
User = get_user_model()

def _truthy(v):
    return str(v).strip().lower() in ("true", "1", "yes", "y", "t")

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

    try:
        checkout_session = stripe.checkout.Session.retrieve(
            session_id,
            expand=['customer']  # setup_intent not used in subscription mode
        )
    except stripe.error.StripeError as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Stripe / metadata
    metadata = checkout_session.get('metadata', {}) or {}
    raw_plan_name = metadata.get('plan_name')
    meta_is_trial = _truthy(metadata.get('is_trial')) if 'is_trial' in metadata else None

    # Prefer DB ("source of truth") if available, else fall back to metadata, else plan-name heuristic
    if hasattr(pending, 'is_trial') and pending.is_trial is not None:
        is_trial = bool(pending.is_trial)
    elif meta_is_trial is not None:
        is_trial = meta_is_trial
    else:
        is_trial = (raw_plan_name == 'adminTrial')

    # Normalize plan name used for billing records
    actual_plan_name = 'adminMonthly' if raw_plan_name == 'adminTrial' else raw_plan_name

    if not actual_plan_name:
        return Response({'error': 'Plan not found in session metadata'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        plan = Plan.objects.get(name=actual_plan_name)
    except Plan.DoesNotExist:
        return Response({'error': 'Plan not found'}, status=status.HTTP_404_NOT_FOUND)

    # Map to your internal subscription_status + get duration in months
    plan_map = {
        'adminMonthly':   ('admin_monthly',   1),
        'adminQuarterly': ('admin_quarterly', 3),
        'adminAnnual':    ('admin_annual',   12),
    }
    subscription_status, months = plan_map.get(actual_plan_name, ('admin_monthly', 1))

    if User.objects.filter(username=email).exists():
        return Response({'error': 'User already exists'}, status=status.HTTP_400_BAD_REQUEST)

    # Create user
    user = User.objects.create_user(username=email, email=email, password=password)
    user.role = 'admin'
    user.is_staff = True
    user.subscription_status = subscription_status
    user.save()

    now = timezone.now()

    # EventTracker (if identity exists)
    admin_identity = AdminIdentity.objects.filter(admin_email=email).first()
    if admin_identity:
        EventTracker.objects.create(
            admin=admin_identity,
            event_type="registration_success",
            timestamp=now
        )

    # ---- Correct date logic ----
    if is_trial:
        trial_start = now
        subscription_start = now + timedelta(days=14)
        subscription_end = subscription_start + relativedelta(months=months)
        next_billing = subscription_start            # first charge happens when trial ends
    else:
        trial_start = None
        subscription_start = now                     # paid period begins immediately
        subscription_end = subscription_start + relativedelta(months=months)
        next_billing = subscription_end              # next charge at end of current period

    # Stripe transaction id from PendingSignup (set by webhook)
    stripe_transaction_id = getattr(pending, 'stripe_transaction_id', None)

    # Create initial billing profile snapshot
    log_profile_event(
        user=user,
        plan=plan,
        stripe_transaction_id=stripe_transaction_id,
        is_trial=is_trial,
        trial_start=trial_start,
        subscription_start=subscription_start,
        subscription_end=subscription_end,
        next_billing=next_billing
    )

    # Finish
    pending.delete()  # burn the token

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
        'dates': {
            'is_trial': is_trial,
            'trial_start': trial_start,
            'subscription_start': subscription_start,
            'subscription_end': subscription_end,
            'next_billing': next_billing,
        }
    }, status=status.HTTP_201_CREATED)
