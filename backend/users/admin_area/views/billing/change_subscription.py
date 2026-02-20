import stripe
from datetime import datetime, timezone as dt_timezone
from django.conf import settings
from django.utils import timezone

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from users.admin_area.models import Profile, Plan, AdminIdentity
from users.admin_area.utils.log_EventTracker import log_EventTracker
from users.admin_area.views.api_contract import error, ok, require_admin
from users.admin_area.views.idempotency import begin_idempotent_request

stripe.api_key = settings.STRIPE_SECRET_KEY

TARGET_MAP = {
    "admin_monthly": "adminMonthly",
    "admin_quarterly": "adminQuarterly",
    "admin_annual": "adminAnnual",
}

CAN_TRANSITION_TO = {
    "admin_monthly": {"admin_quarterly", "admin_annual"},
    "admin_quarterly": {"admin_monthly", "admin_annual"},
    "admin_annual": {"admin_monthly", "admin_quarterly"},
}


def _admin_id_for_user(user) -> str | None:
    ident, _ = AdminIdentity.objects.get_or_create(admin_email=getattr(user, "email", ""))
    return str(ident.adminID)


def _active_subscription_for_admin_id(admin_id: str):
    try:
        custs = stripe.Customer.search(query=f"metadata['admin_id']:'{admin_id}'", limit=1)
        if custs and custs.data:
            subs = stripe.Subscription.list(customer=custs.data[0].id, status="active", limit=1)
            if subs and subs.data:
                return subs.data[0]
    except Exception:
        pass
    return None


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_subscription(request):
    auth_error = require_admin(request)
    if auth_error:
        return auth_error
    user = request.user
    replay_response, finalize = begin_idempotent_request(
        request,
        namespace="change_subscription",
        actor=getattr(user, "email", "") or f"user-{getattr(user, 'id', 'unknown')}",
    )
    if replay_response:
        return replay_response

    target_plan = (request.data or {}).get("target_plan")
    if target_plan not in TARGET_MAP:
        return finalize(
            error(code="INVALID_TARGET_PLAN", message="Invalid target plan.", http_status=status.HTTP_400_BAD_REQUEST)
        )

    try:
        active_profile = user.profiles.get(is_active=True)
    except Profile.DoesNotExist:
        return finalize(
            error(code="PROFILE_NOT_FOUND", message="Admin profile not found.", http_status=status.HTTP_404_NOT_FOUND)
        )

    if active_profile.is_trial:
        return finalize(
            error(
                code="TRIAL_CHECKOUT_REQUIRED",
                message="Trial upgrades use checkout. This endpoint is for paid plan changes only.",
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        )

    current_status = getattr(user, "subscription_status", "")
    allowed = CAN_TRANSITION_TO.get(current_status, set())
    if target_plan not in allowed:
        return finalize(
            error(
                code="TRANSITION_NOT_ALLOWED",
                message="This plan transition is not allowed.",
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        )

    target_model_name = TARGET_MAP[target_plan]
    target_plan_obj = Plan.objects.filter(name=target_model_name).first()
    if not target_plan_obj:
        return finalize(
            error(
                code="TARGET_PLAN_NOT_CONFIGURED",
                message="Target plan is not configured.",
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        )

    admin_id = _admin_id_for_user(user)
    sub = _active_subscription_for_admin_id(admin_id) if admin_id else None
    if not sub:
        return finalize(
            error(
                code="NO_ACTIVE_SUBSCRIPTION",
                message="No active Stripe subscription found.",
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        )

    sub_id = sub.get("id")
    curr_end = sub.get("current_period_end")
    current_price_id = None
    try:
        full_sub = stripe.Subscription.retrieve(sub_id, expand=["items.data.price"])
        items = (full_sub.get("items") or {}).get("data") or []
        current_price_id = items[0]["price"]["id"] if items else None
        curr_end = full_sub.get("current_period_end") or curr_end
        existing_schedule = full_sub.get("schedule")
        if existing_schedule:
            try:
                stripe.SubscriptionSchedule.release(existing_schedule)
            except Exception:
                pass
    except Exception:
        return finalize(
            error(
                code="SUBSCRIPTION_DETAILS_UNAVAILABLE",
                message="Could not load current subscription details.",
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        )

    if not current_price_id or not curr_end:
        return finalize(
            error(
                code="BILLING_BOUNDARY_UNAVAILABLE",
                message="Could not determine billing cycle boundary.",
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        )

    try:
        stripe.SubscriptionSchedule.create(
            from_subscription=sub_id,
            phases=[
                {
                    "items": [{"price": current_price_id, "quantity": 1}],
                    "start_date": "now",
                    "end_date": curr_end,
                },
                {
                    "items": [{"price": target_plan_obj.stripe_price_id, "quantity": 1}],
                },
            ],
            metadata={
                "admin_id": admin_id or "",
                "scheduled_change": "1",
                "target_plan": target_plan,
            },
        )
    except Exception:
        return finalize(
            error(
                code="PLAN_CHANGE_SCHEDULE_FAILED",
                message="Failed to schedule plan change.",
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        )

    pending = user.profiles.filter(is_active=False).order_by("-created_at").first()
    effective_at = datetime.fromtimestamp(curr_end, tz=dt_timezone.utc)
    if pending:
        pending.plan = target_plan_obj
        pending.subscription_start = effective_at
        pending.is_trial = False
        pending.is_canceled = False
        pending.save()
    else:
        Profile.objects.create(
            user=user,
            plan=target_plan_obj,
            is_active=False,
            is_trial=False,
            is_canceled=False,
            subscription_start=effective_at,
        )

    log_EventTracker(
        admin_email=user.email,
        event_type="plan_change_scheduled_no_checkout",
        details=f"from_status={current_status} to_status={target_plan} effective_at={curr_end}",
    )

    return finalize(
        ok(
            {
                "message": "Plan change scheduled. Current plan remains active until this cycle ends.",
                "scheduled_for": effective_at,
                "target_plan": target_plan,
            },
            http_status=200,
        )
    )
