import json
import re
import stripe
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from users.admin_area.models import Plan, PendingSignup, AdminIdentity, EventTracker
from users.admin_area.utils.log_Profile import log_Profile
from users.admin_area.views.api_contract import ok, error
from core.services.google_oauth import verify_google_id_token

stripe.api_key = settings.STRIPE_SECRET_KEY
User = get_user_model()
SUBDOMAIN_SLUG_RE = re.compile(r"^[a-z]+(?:-[a-z]+)*$")
RESERVED_SUBDOMAIN_SLUGS = {
    "www",
    "admin",
    "api",
    "app",
    "support",
    "mail",
    "static",
}

def _is_gmail_email(value):
    email = (value or '').strip().lower()
    return email.endswith('@gmail.com') or email.endswith('@googlemail.com')


def _is_dta_house_admin_email(value):
    return (value or '').strip().lower() == 'admin@dta.com'


def _validate_subdomain_slug(raw_slug):
    slug = str(raw_slug or '').strip().lower()
    if not slug:
        return None, 'Subdomain is required.'
    if ' ' in slug:
        return None, 'Subdomain cannot contain spaces.'
    if len(slug) < 3 or len(slug) > 40:
        return None, 'Subdomain must be between 3 and 40 characters.'
    if slug in RESERVED_SUBDOMAIN_SLUGS:
        return None, 'That subdomain is reserved. Please choose another.'
    if not SUBDOMAIN_SLUG_RE.fullmatch(slug):
        return None, 'Use only letters and hyphens (no numbers, spaces, or underscores).'
    return slug, None


def _assign_subdomain_once(identity, raw_slug):
    if identity.subdomain_slug:
        existing = (identity.subdomain_slug or '').strip().lower()
        incoming, err = _validate_subdomain_slug(raw_slug)
        if err:
            return None, err
        if incoming != existing:
            return None, 'Subdomain is locked and can only be set once.'
        return identity.subdomain_slug, None

    slug, err = _validate_subdomain_slug(raw_slug)
    if err:
        return None, err

    identity.subdomain_slug = slug
    identity.subdomain_locked_at = timezone.now()
    try:
        identity.save(update_fields=['subdomain_slug', 'subdomain_locked_at'])
    except IntegrityError:
        return None, 'That subdomain is already taken. Please choose another.'
    return identity.subdomain_slug, None

def _truthy(v):
    return str(v).strip().lower() in ("true", "1", "yes", "y", "t")

def _ts_to_aware(ts):
    if not ts:
        return None
    # Stripe timestamps are seconds since epoch (UTC)
    from datetime import datetime
    from django.utils import timezone
    return timezone.make_aware(datetime.utcfromtimestamp(ts))


def _normalize_admin_plan_name(value):
    raw = str(value or '').strip()
    if not raw:
        return ''
    aliases = {
        'adminTrial': 'adminTrial',
        'admin_trial': 'adminTrial',
        'adminMonthly': 'adminMonthly',
        'admin_monthly': 'adminMonthly',
        'adminQuarterly': 'adminQuarterly',
        'admin_quarterly': 'adminQuarterly',
        'adminAnnual': 'adminAnnual',
        'admin_annual': 'adminAnnual',
    }
    return aliases.get(raw, raw)


def _plan_name_from_session_or_subscription(checkout_session):
    # Fallback resolver when metadata/pending signup plan is missing.
    try:
        line_items = stripe.checkout.Session.list_line_items(checkout_session.get('id'), limit=3)
        for item in list((line_items or {}).get('data', []) or []):
            price_field = (item or {}).get('price')
            price_id = (price_field if isinstance(price_field, str) else ((price_field or {}).get('id') or '')).strip()
            if price_id:
                plan = Plan.objects.filter(stripe_price_id=price_id).first()
                if plan:
                    return plan.name
    except Exception as exc:
        print("STRIPE LINE ITEM PLAN RESOLVE ERROR:", exc)

    sub_id = checkout_session.get('subscription')
    if sub_id:
        try:
            sub = stripe.Subscription.retrieve(sub_id)
            for sub_item in list(((sub or {}).get('items') or {}).get('data', []) or []):
                price_id = ((((sub_item or {}).get('price')) or {}).get('id') or '').strip()
                if price_id:
                    plan = Plan.objects.filter(stripe_price_id=price_id).first()
                    if plan:
                        return plan.name
        except Exception as exc:
            print("STRIPE SUB PLAN RESOLVE ERROR:", exc)

    return ''

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    data = request.data
    email = (data.get('email') or '').strip().lower()
    password = data.get('password')
    token = data.get('token')
    credential = (data.get('credential') or '').strip()
    subdomain_slug = data.get('subdomain_slug')

    if not email or not token or (not password and not credential):
        return error(code='MISSING_FIELDS', message='Email, token, and password or Google credential are required.', http_status=status.HTTP_400_BAD_REQUEST)
    if _is_gmail_email(email) and not credential:
        return error(code='GOOGLE_REQUIRED', message='Gmail accounts must continue with Google.', http_status=status.HTTP_400_BAD_REQUEST)

    if credential:
        try:
            google_payload = verify_google_id_token(credential)
        except RuntimeError as exc:
            return error(code='GOOGLE_CONFIG_ERROR', message=str(exc), http_status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except ValueError as exc:
            return error(code='INVALID_GOOGLE_TOKEN', message=str(exc), http_status=status.HTTP_401_UNAUTHORIZED)
        google_email = (google_payload.get('email') or '').strip().lower()
        email_verified = bool(google_payload.get('email_verified'))
        if not google_email or not email_verified:
            return error(code='GOOGLE_EMAIL_UNVERIFIED', message='Google email is missing or not verified.', http_status=status.HTTP_401_UNAUTHORIZED)
        if google_email != email:
            return error(code='EMAIL_TOKEN_MISMATCH', message='Google account email does not match this registration link.', http_status=status.HTTP_400_BAD_REQUEST)

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
    if not raw_plan_name:
        raw_plan_name = getattr(pending, 'plan', None)
    if not raw_plan_name:
        raw_plan_name = _plan_name_from_session_or_subscription(checkout_session)
    meta_is_trial = _truthy(metadata.get('is_trial')) if 'is_trial' in metadata else None

    # Decide trial flag
    if hasattr(pending, 'is_trial') and pending.is_trial is not None:
        is_trial = bool(pending.is_trial)
    elif meta_is_trial is not None:
        is_trial = meta_is_trial
    else:
        is_trial = (raw_plan_name == 'adminTrial')

    # Normalize plan
    normalized_plan_name = _normalize_admin_plan_name(raw_plan_name)
    actual_plan_name = 'adminMonthly' if normalized_plan_name == 'adminTrial' else normalized_plan_name
    if not actual_plan_name:
        return error(
            code='PLAN_NOT_FOUND',
            message='Plan not found in checkout metadata, pending signup record, or Stripe line items',
            http_status=status.HTTP_400_BAD_REQUEST,
        )

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

    admin_identity, _ = AdminIdentity.objects.get_or_create(admin_email=email)
    if not _is_dta_house_admin_email(email):
        _, subdomain_error = _assign_subdomain_once(admin_identity, subdomain_slug)
        if subdomain_error:
            return error(code='INVALID_SUBDOMAIN_SLUG', message=subdomain_error, http_status=status.HTTP_400_BAD_REQUEST)

    # Create user
    if credential:
        user = User.objects.create_user(username=email, email=email)
        user.set_unusable_password()
    else:
        user = User.objects.create_user(username=email, email=email, password=password)
    user.role = 'admin'
    user.is_staff = True
    user.subscription_status = subscription_status
    user.save()

    now = timezone.now()

    # EventTracker
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
