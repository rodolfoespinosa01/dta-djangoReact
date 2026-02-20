import stripe
from datetime import datetime, timezone as dt_timezone
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from users.admin_area.views.api_contract import error, ok, require_admin
from users.admin_area.views.idempotency import begin_idempotent_request

from users.admin_area.models import Profile, AdminIdentity, EventTracker, Plan

stripe.api_key = settings.STRIPE_SECRET_KEY


def _ts(ts: int | None):
    return datetime.fromtimestamp(ts, tz=dt_timezone.utc) if ts else None


PLAN_NAME_TO_STATUS = {
    "adminMonthly": "admin_monthly",
    "adminQuarterly": "admin_quarterly",
    "adminAnnual": "admin_annual",
}


def _active_subscription_for_admin_email(email: str):
    wanted_status = ("active", "past_due", "trialing")

    def _pick(subs):
        if not subs:
            return None
        for st in wanted_status:
            for sub in subs:
                if sub.get("status") == st:
                    return sub
        return None

    try:
        ident = AdminIdentity.objects.filter(admin_email=email).first()
        if ident:
            custs = stripe.Customer.search(query=f"metadata['admin_id']:'{ident.adminID}'", limit=1)
            if custs and custs.data:
                subs = stripe.Subscription.list(customer=custs.data[0].id, status="all", limit=20)
                picked = _pick(subs.data or [])
                if picked:
                    return picked
    except Exception:
        pass

    return None


def _plan_from_subscription_id(sub_id: str | None):
    if not sub_id:
        return None
    try:
        sub = stripe.Subscription.retrieve(sub_id, expand=["items.data.price"])
        items = (sub.get("items") or {}).get("data") or []
        price_id = items[0].get("price", {}).get("id") if items else None
        if not price_id:
            return None
        return Plan.objects.filter(stripe_price_id=price_id).first()
    except Exception:
        return None


def _subscription_snapshot(sub_id: str | None):
    if not sub_id:
        return None
    try:
        sub = stripe.Subscription.retrieve(sub_id, expand=["items.data.price"])
    except Exception:
        return None

    items = (sub.get("items") or {}).get("data") or []
    price_id = items[0].get("price", {}).get("id") if items else None
    plan = Plan.objects.filter(stripe_price_id=price_id).first() if price_id else None
    return {
        "id": sub.get("id"),
        "status": sub.get("status"),
        "plan": plan,
        "current_period_end": _ts(sub.get("current_period_end")),
    }


def _clear_subscription_schedule(sub_id: str | None):
    if not sub_id:
        return
    try:
        sub = stripe.Subscription.retrieve(sub_id)
        schedule_id = sub.get("schedule")
        if schedule_id:
            try:
                stripe.SubscriptionSchedule.release(schedule_id)
            except Exception:
                pass
    except Exception:
        pass


def _snapshot(p: Profile):
    return {
        "is_trial": bool(p.is_trial),
        "subscription_active": bool(p.is_active),
        "is_canceled": bool(p.is_canceled),
        "subscription_end": p.subscription_end,
        "next_billing": p.next_billing,
        "is_active": bool(p.is_active),
    }


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cancel_subscription(request):
    auth_error = require_admin(request)
    if auth_error:
        return auth_error

    user = request.user
    replay_response, finalize = begin_idempotent_request(
        request,
        namespace="cancel_subscription",
        actor=getattr(user, "email", "") or f"user-{getattr(user, 'id', 'unknown')}",
    )
    if replay_response:
        return replay_response

    active_profiles = user.profiles.filter(is_active=True).order_by("-created_at")
    profile = active_profiles.filter(is_trial=False).first() or active_profiles.first()
    if not profile:
        return finalize(error(code="PROFILE_NOT_FOUND", message="No active profile found.", http_status=404))

    # Idempotent
    if profile.is_canceled:
        return finalize(ok({"message": "already canceled", "snapshot": _snapshot(profile)}, http_status=200))

    picked_sub = _active_subscription_for_admin_email(user.email)
    sub_id = picked_sub.get("id") if picked_sub else None
    cycle_end = profile.next_billing or profile.subscription_end
    sub_snap = _subscription_snapshot(sub_id)

    # Reconcile local state from Stripe first so stale trial rows never drive cancellation logic.
    if sub_snap and sub_snap.get("plan"):
        sub_plan = sub_snap["plan"]
        sub_status = sub_snap.get("status")
        sub_is_trial = (sub_status == "trialing")
        sub_cycle_end = sub_snap.get("current_period_end")
        with transaction.atomic():
            user.profiles.filter(is_active=True).update(is_active=False)
            profile = Profile.objects.create(
                user=user,
                plan=sub_plan,
                is_active=True,
                is_trial=sub_is_trial,
                is_canceled=False,
                subscription_start=timezone.now(),
                subscription_end=None,
                next_billing=sub_cycle_end,
            )
            mapped = PLAN_NAME_TO_STATUS.get(sub_plan.name)
            if mapped:
                user.subscription_status = mapped
                user.save(update_fields=["subscription_status"])
        cycle_end = sub_cycle_end or cycle_end

    if sub_id:
        try:
            _clear_subscription_schedule(sub_id)
            sub = stripe.Subscription.retrieve(sub_id)
            if not bool(sub.get("cancel_at_period_end")) and sub.get("status") in ("trialing", "active", "past_due"):
                sub = stripe.Subscription.modify(sub_id, cancel_at_period_end=True)
            cycle_end = _ts(sub.get("current_period_end")) or cycle_end
        except Exception:
            pass

    with transaction.atomic():
        # Keep one authoritative active profile to avoid trial/paid conflicts in UI logic.
        user.profiles.filter(is_active=True).exclude(pk=profile.pk).update(is_active=False)
        profile.is_canceled = True
        profile.subscription_end = cycle_end
        profile.is_active = True  # keep access until cycle end; dashboard handles lockout at expiry
        profile.save(update_fields=["is_canceled", "subscription_end", "is_active"])
        # If a future plan switch was pending, cancellation should remove all auto-renew/next-plan behavior.
        user.profiles.filter(is_active=False, subscription_start__isnull=False).update(is_canceled=True)
        _log_cancel_event(user.email, cycle_end, profile.is_trial)

    return finalize(
        ok(
            {"message": "auto-renew canceled", "snapshot": _snapshot(profile)},
            http_status=200,
        )
    )


def _log_cancel_event(email: str, active_until_dt, is_trial: bool):
    ts = active_until_dt.isoformat() if active_until_dt else ""
    admin, _ = AdminIdentity.objects.get_or_create(admin_email=email)
    EventTracker.objects.create(
        admin=admin,
        event_type="cancel_subscription",
        details=f"plan_type={'trial' if is_trial else 'paid'} active_until={ts}",
    )
