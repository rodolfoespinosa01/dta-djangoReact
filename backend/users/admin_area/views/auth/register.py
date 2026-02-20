import json
import stripe
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from django.contrib.auth import get_user_model

from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from users.admin_area.models import Plan, PendingSignup, AdminIdentity, EventTracker
from users.admin_area.utils.log_Profile import log_Profile
from users.admin_area.views.api_contract import ok, error

stripe.api_key = settings.STRIPE_SECRET_KEY
User = get_user_model()

def _truthy(v):
    return str(v).strip().lower() in ("true", "1", "yes", "y", "t")

def _ts_to_aware(ts):
    if not ts:
        return None
    # Stripe timestamps are seconds since epoch (UTC)
    from datetime import datetime
    from django.utils import timezone
    return timezone.make_aware(datetime.utcfromtimestamp(ts))

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    data = request.data
    email = data.get('email')
    password = data.get('password')
    token = data.get('token')

    if not all([email, password, token]):
        return error(code='MISSING_FIELDS', message='Missing fields', http_status=status.HTTP_400_BAD_REQUEST)

    try:
        pending = PendingSignup.objects.get(token=token)
    except PendingSignup.DoesNotExist:
        return error(code='INVALID_TOKEN', message='Invalid or expired token', http_status=status.HTTP_404_NOT_FOUND)

    session_id = pending.session_id

    try:
        checkout_session = stripe.checkout.Session.retrieve(
            session_id,
            expand=['customer']  # session has a 'subscription' id we can fetch next
        )
    except stripe.error.StripeError as e:
        return error(code='STRIPE_ERROR', message=str(e), http_status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Stripe / metadata
    metadata = checkout_session.get('metadata', {}) or {}
    raw_plan_name = metadata.get('plan_name')
    meta_is_trial = _truthy(metadata.get('is_trial')) if 'is_trial' in metadata else None

    # Decide trial flag
    if hasattr(pending, 'is_trial') and pending.is_trial is not None:
        is_trial = bool(pending.is_trial)
    elif meta_is_trial is not None:
        is_trial = meta_is_trial
    else:
        is_trial = (raw_plan_name == 'adminTrial')

    # Normalize plan
    actual_plan_name = 'adminMonthly' if raw_plan_name == 'adminTrial' else raw_plan_name
    if not actual_plan_name:
        return error(code='PLAN_NOT_FOUND', message='Plan not found in session metadata', http_status=status.HTTP_400_BAD_REQUEST)

    try:
        plan = Plan.objects.get(name=actual_plan_name)
    except Plan.DoesNotExist:
        return error(code='PLAN_NOT_FOUND', message='Plan not found', http_status=status.HTTP_404_NOT_FOUND)

    # Map to internal label
    plan_map = {
        'adminMonthly':   'admin_monthly',
        'adminQuarterly': 'admin_quarterly',
        'adminAnnual':    'admin_annual',
    }
    subscription_status = plan_map.get(actual_plan_name, 'admin_monthly')

    if User.objects.filter(username=email).exists():
        return error(code='USER_EXISTS', message='User already exists', http_status=status.HTTP_400_BAD_REQUEST)

    # Create user
    user = User.objects.create_user(username=email, email=email, password=password)
    user.role = 'admin'
    user.is_staff = True
    user.subscription_status = subscription_status
    user.save()

    now = timezone.now()

    # EventTracker
    admin_identity = AdminIdentity.objects.filter(admin_email=email).first()
    if admin_identity:
        EventTracker.objects.create(
            admin=admin_identity,
            event_type="registration_success",
            timestamp=now
        )

    # ---------- Accurate date stamping from Stripe Subscription ----------
    trial_start = None
    subscription_start = None
    subscription_end = None
    next_billing = None

    sub_id = checkout_session.get('subscription')
    if sub_id:
        try:
            # pull the latest invoice line period as a fallback
            sub = stripe.Subscription.retrieve(
                sub_id,
                expand=['latest_invoice.lines']
            )

            status_val = sub.get('status')  # 'trialing' | 'active' | 'incomplete' | ...
            cur_start = _ts_to_aware(sub.get('current_period_start'))
            cur_end   = _ts_to_aware(sub.get('current_period_end'))
            trial_end = _ts_to_aware(sub.get('trial_end'))

            # Fallbacks from latest invoice line
            li_start = li_end = None
            try:
                line_period = (sub.get('latest_invoice') or {}).get('lines', {}).get('data', [])[0].get('period', {})
                li_start = _ts_to_aware(line_period.get('start'))
                li_end   = _ts_to_aware(line_period.get('end'))
            except Exception:
                pass

            if status_val == 'trialing' or is_trial:
                is_trial = True
                trial_start = cur_start or li_start or now
                next_billing = trial_end or li_end or cur_end or (now + timedelta(days=14))
                subscription_start = None
                subscription_end = None
            else:
                is_trial = False
                subscription_start = cur_start or li_start or now
                next_billing = cur_end or li_end  # <- this is the important fallback
                subscription_end = None

        except Exception as e:
            print("STRIPE SUB ERROR:", e)
            # Fallbacks if we can’t fetch sub cleanly
            if is_trial:
                trial_start = now
                next_billing = now + timedelta(days=14)
            else:
                subscription_start = None
                next_billing = None
    else:
        # No subscription id on session (rare) → fall back
        if is_trial:
            trial_start = now
            next_billing = now + timedelta(days=14)
        else:
            subscription_start = None
            next_billing = None


    # Stripe transaction id from PendingSignup (set by webhook)
    stripe_transaction_id = getattr(pending, 'stripe_transaction_id', None)

    # Create initial Profile snapshot (never pass None for is_canceled)
    log_Profile(
        user=user,
        plan=plan,
        stripe_transaction_id=stripe_transaction_id,
        is_trial=is_trial,
        trial_start=trial_start,
        subscription_start=subscription_start,
        subscription_end=subscription_end,
        next_billing=next_billing,
        is_canceled=False,
    )

    # Burn token
    pending.delete()

    # JWTs
    refresh = RefreshToken.for_user(user)
    refresh['email'] = user.email
    refresh['role'] = user.role
    refresh['subscription_status'] = user.subscription_status

    return ok({
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
    }, http_status=status.HTTP_201_CREATED)
