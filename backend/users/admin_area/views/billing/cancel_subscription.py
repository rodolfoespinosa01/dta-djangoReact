# backend/users/admin_area/views/billing/cancel_subscription.py
import stripe
from datetime import datetime
from django.conf import settings
from django.utils import timezone
from django.db import transaction

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from users.admin_area.models import Profile, EventTracker, AdminIdentity

stripe.api_key = settings.STRIPE_SECRET_KEY


def _ts(ts):
    return timezone.make_aware(datetime.utcfromtimestamp(ts)) if ts else None


def _snapshot(p: Profile):
    return {
        "is_trial": bool(p.is_trial),
        "subscription_active": bool(p.subscription_active),
        "is_canceled": bool(p.is_canceled),
        "auto_renew": bool(getattr(p, "auto_renew", True)),
        "subscription_end": p.subscription_end,
        "next_billing": p.next_billing,
        "is_active": bool(p.is_active),
    }


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cancel_subscription(request):
    user = request.user
    try:
        profile = user.profiles.get(is_active=True)
    except Profile.DoesNotExist:
        return Response({"error": "No active profile found."}, status=404)

    # Idempotent: if already canceled, just return snapshot
    if profile.is_canceled is True or getattr(profile, "auto_renew", True) is False:
        return Response({"message": "already canceled", "snapshot": _snapshot(profile)}, status=200)

    sub_id = getattr(profile, "stripe_subscription_id", None)

    # ===== TRIAL USERS → cancel now + lock out =====
    if profile.is_trial:
        with transaction.atomic():
            # Try to cancel at Stripe immediately if a sub exists (trialing)
            if sub_id:
                try:
                    sub = stripe.Subscription.retrieve(sub_id)
                    if sub.get("status") in ("trialing", "active"):
                        stripe.Subscription.delete(sub_id)
                except Exception:
                    # Don't block on Stripe errors for trial immediate cancel
                    pass

            now = timezone.now()
            profile.is_trial = False
            profile.subscription_active = False
            profile.is_canceled = True
            profile.subscription_end = now
            profile.next_billing = None
            profile.is_active = False          # 🔒 lock dashboard now
            profile.save()
            _log_cancel_event(user.email, now)

        return Response(
            {"message": "trial canceled immediately", "snapshot": _snapshot(profile)},
            status=200
        )

    # ===== PAID USERS → schedule end, keep access =====
    # Determine end date from Stripe (preferred) or fall back to existing next_billing
    cur_end = None
    if sub_id:
        try:
            sub = stripe.Subscription.retrieve(sub_id)
            # If not already scheduled, set cancel_at_period_end
            if not bool(sub.get("cancel_at_period_end")) and sub.get("status") == "active":
                sub = stripe.Subscription.modify(sub_id, cancel_at_period_end=True)
            cur_end = _ts(sub.get("current_period_end"))
        except Exception as e:
            # Fallback to what we already have locally
            cur_end = profile.next_billing or profile.subscription_end
    else:
        # No Stripe sub id (edge case) → use next_billing as end if available
        cur_end = profile.next_billing or profile.subscription_end

    with transaction.atomic():
        profile.is_trial = False
        profile.subscription_active = True     # still active on Stripe until period end
        profile.is_canceled = True
        if cur_end:
            profile.subscription_end = cur_end # end at period end
        profile.next_billing = None            # no more renewals shown
        profile.is_active = True               # ✅ keep dashboard access
        profile.save()
        _log_cancel_event(user.email, profile.subscription_end or timezone.now())

    return Response({"message": "auto-renew canceled", "snapshot": _snapshot(profile)}, status=200)


def _log_cancel_event(email: str, active_until_dt):
    ts = active_until_dt.isoformat() if active_until_dt else ""
    admin, _ = AdminIdentity.objects.get_or_create(admin_email=email)
    EventTracker.objects.create(
        admin=admin,
        event_type="cancel_subscription",
        details=f"active_until={ts}",
    )
