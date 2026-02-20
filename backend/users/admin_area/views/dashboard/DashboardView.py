import stripe
from datetime import datetime, timezone as dt_timezone
from django.conf import settings
from django.utils.timezone import now
from rest_framework.views import APIView
from rest_framework import permissions, status

from users.admin_area.models import Profile, AdminIdentity, Plan
from users.admin_area.serializers.contracts import AdminDashboardPayloadSerializer
from users.admin_area.views.api_contract import error, ok, require_admin

stripe.api_key = settings.STRIPE_SECRET_KEY

PLAN_NAME_TO_STATUS = {
    "adminMonthly": "admin_monthly",
    "adminQuarterly": "admin_quarterly",
    "adminAnnual": "admin_annual",
}


def _ts(ts):
    return datetime.fromtimestamp(ts, tz=dt_timezone.utc) if ts else None


def _stripe_customer_for_email(email: str):
    ident = AdminIdentity.objects.filter(admin_email=email).first()
    if ident:
        try:
            res = stripe.Customer.search(query=f"metadata['admin_id']:'{ident.adminID}'", limit=1)
            if res and res.data:
                return res.data[0]
        except Exception:
            pass
    return None


def _stripe_current_subscription(email: str):
    customer = _stripe_customer_for_email(email)
    if not customer:
        return None

    try:
        subs = stripe.Subscription.list(customer=customer.id, status="all", limit=30)
    except Exception:
        return None

    # Prefer paid active states over trialing when both exist.
    status_priority = ["active", "past_due", "trialing", "unpaid", "canceled", "incomplete"]
    picked = None
    for wanted in status_priority:
        for sub in (subs.data or []):
            if sub.get("status") == wanted:
                picked = sub
                break
        if picked:
            break
    if not picked:
        return None

    try:
        full = stripe.Subscription.retrieve(picked.get("id"), expand=["items.data.price"])
    except Exception:
        full = picked

    items = (full.get("items") or {}).get("data") or []
    price_id = items[0].get("price", {}).get("id") if items else None
    plan = Plan.objects.filter(stripe_price_id=price_id).first() if price_id else None
    return {
        "id": full.get("id"),
        "status": full.get("status"),
        "cancel_at_period_end": bool(full.get("cancel_at_period_end")),
        "current_period_end": _ts(full.get("current_period_end")),
        "plan": plan,
    }


class DashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        auth_error = require_admin(request)
        if auth_error:
            return auth_error
        user = request.user

        now_ts = now()
        stripe_sub = _stripe_current_subscription(user.email)

        # DB fallback profile
        active_profiles = user.profiles.filter(is_active=True).order_by("-created_at")
        profile = active_profiles.filter(is_trial=False).first() or active_profiles.first()
        if not profile:
            return error(
                code="PROFILE_NOT_FOUND",
                message="Admin profile not found.",
                http_status=status.HTTP_404_NOT_FOUND,
            )

        data_source = "db_fallback"
        # Source of truth: Stripe first.
        if stripe_sub and stripe_sub.get("plan"):
            data_source = "stripe"
            stripe_plan = stripe_sub["plan"]
            stripe_status = stripe_sub.get("status")
            subscription_status = PLAN_NAME_TO_STATUS.get(stripe_plan.name, getattr(user, "subscription_status", ""))
            is_trial = (stripe_status == "trialing")
            is_canceled = bool(stripe_sub.get("cancel_at_period_end"))
            cycle_end = stripe_sub.get("current_period_end")
            is_active = bool(cycle_end is None or cycle_end > now_ts)
            next_billing = None if is_canceled else cycle_end
            period_end = cycle_end if is_canceled else None
            current_cycle_ends_on = cycle_end
            days_left_in_cycle = max((cycle_end - now_ts).days, 0) if cycle_end else None
            trial_start = profile.trial_start if is_trial else None
            trial_ends_on = cycle_end if is_trial else None
            days_remaining = max((cycle_end - now_ts).days, 0) if (is_trial and cycle_end) else None
        else:
            profile_is_trial = bool(getattr(profile, "is_trial", False))
            profile_plan_name = getattr(getattr(profile, "plan", None), "name", None)
            # Prefer latest paid profile plan if present to avoid stale-trial reads.
            latest_paid = user.profiles.filter(is_active=True, is_trial=False, plan__isnull=False).order_by("-created_at").first()
            latest_paid_status = None
            if latest_paid and latest_paid.plan:
                latest_paid_status = PLAN_NAME_TO_STATUS.get(getattr(latest_paid.plan, "name", None))
            raw_status = latest_paid_status or PLAN_NAME_TO_STATUS.get(profile_plan_name) or getattr(user, "subscription_status", "")
            subscription_status = "admin_trial" if profile_is_trial else raw_status
            is_trial = (subscription_status == "admin_trial")
            is_canceled = bool(getattr(profile, "is_canceled", False))
            period_end = getattr(profile, "subscription_end", None)
            next_billing = getattr(profile, "next_billing", None)
            trial_ends_on = next_billing if is_trial else None
            current_cycle_ends_on = period_end or next_billing
            days_left_in_cycle = max((current_cycle_ends_on - now_ts).days, 0) if current_cycle_ends_on else None
            days_remaining = max((trial_ends_on - now_ts).days, 0) if trial_ends_on else None
            expired = bool(current_cycle_ends_on and current_cycle_ends_on <= now_ts)
            is_active = not expired
            trial_start = profile.trial_start if is_trial else None

        # Upcoming plan (scheduled local pending profile)
        pending = (
            user.profiles
            .filter(is_active=False, plan__isnull=False, is_canceled=False, subscription_start__gt=now_ts)
            .order_by("subscription_start")
            .first()
        )
        next_plan_status = None
        next_plan_price_cents = None
        next_plan_effective_on = current_cycle_ends_on
        if is_canceled:
            next_plan_status = None
            next_plan_price_cents = None
        elif pending and pending.plan:
            next_plan_status = PLAN_NAME_TO_STATUS.get(getattr(pending.plan, "name", None))
            next_plan_price_cents = getattr(pending.plan, "price_cents", None)
            next_plan_effective_on = pending.subscription_start
        else:
            # Active trial should still show the selected post-trial plan and charge.
            next_plan_status = subscription_status
            base_plan = stripe_sub.get("plan") if stripe_sub else getattr(profile, "plan", None)
            if base_plan:
                next_plan_price_cents = getattr(base_plan, "price_cents", None)

        trial_converts_to = next_plan_status if is_trial else None
        if is_trial and is_canceled:
            trial_converts_to = None

        payload = {
            "subscription_status": "admin_trial" if is_trial else subscription_status,
            "subscription_active": is_active,
            "is_active": is_active,
            "is_canceled": is_canceled,
            "cancel_at_period_end": is_canceled,
            "subscription_end": period_end,
            "next_billing": next_billing if is_active else None,
            "is_trial": is_trial and is_active,
            "days_remaining": days_remaining,
            "trial_start": trial_start,
            "trial_ends_on": trial_ends_on,
            "trial_converts_to": trial_converts_to,
            "monthly_start": profile.subscription_start if subscription_status == "admin_monthly" else None,
            "quarterly_start": profile.subscription_start if subscription_status == "admin_quarterly" else None,
            "annual_start": profile.subscription_start if subscription_status == "admin_annual" else None,
            "auto_renew": not is_canceled,
            "current_cycle_ends_on": current_cycle_ends_on,
            "days_left_in_cycle": days_left_in_cycle,
            "next_plan_status": next_plan_status,
            "next_plan_price_cents": next_plan_price_cents,
            "next_plan_effective_on": next_plan_effective_on,
        }

        if settings.DEBUG:
            payload["debug_data_source"] = data_source
            payload["debug_stripe_status"] = stripe_sub.get("status") if stripe_sub else None
            payload["debug_stripe_plan"] = getattr(stripe_sub.get("plan"), "name", None) if stripe_sub else None
            payload["debug_profile_id"] = str(profile.profile_id) if hasattr(profile, "profile_id") else None

        payload_serializer = AdminDashboardPayloadSerializer(data=payload)
        if not payload_serializer.is_valid():
            return error(
                code="DASHBOARD_PAYLOAD_INVALID",
                message="Dashboard payload validation failed.",
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details=payload_serializer.errors,
            )

        safe_payload = payload_serializer.validated_data
        if not is_active:
            return error(
                code="SUBSCRIPTION_INACTIVE",
                message="Subscription is inactive.",
                http_status=status.HTTP_403_FORBIDDEN,
                extra=safe_payload,
            )
        return ok(safe_payload, http_status=status.HTTP_200_OK)
