import stripe
from datetime import datetime, timedelta, timezone as dt_timezone
from django.conf import settings
from django.utils.timezone import now
from django.db.models import Count, Prefetch
from rest_framework.views import APIView
from rest_framework import permissions, status

from users.admin_area.models import Profile, AdminIdentity, Plan
from users.client_area.models import (
    ClientMealPlanGenerationJob,
    ClientPendingSignup,
    ClientProfile,
    ClientProgressPhoto,
    ClientQuestionnaireProgress,
    ClientWeightEntry,
)
from users.admin_area.serializers.contracts import AdminDashboardPayloadSerializer
from users.admin_area.views.api_contract import error, ok, require_admin

stripe.api_key = settings.STRIPE_SECRET_KEY

PLAN_NAME_TO_STATUS = {
    "adminMonthly": "admin_monthly",
    "adminQuarterly": "admin_quarterly",
    "adminAnnual": "admin_annual",
}
DAY_ORDER = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
DAY_INDEX = {day: idx for idx, day in enumerate(DAY_ORDER)}


def _ts(ts):
    return datetime.fromtimestamp(ts, tz=dt_timezone.utc) if ts else None


def _iso(value):
    return value.isoformat() if value else None


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


def _sorted_days(days):
    return sorted(set(days), key=lambda value: DAY_INDEX.get(value, 99))


def _questionnaire_snapshot(user):
    try:
        progress = user.questionnaire_progress
    except ClientQuestionnaireProgress.DoesNotExist:
        progress = None
    return {
        "status": getattr(progress, "status", "not_started"),
        "completed_at": _iso(getattr(progress, "completed_at", None)),
    }


def _build_client_funnel_payload(admin_identity):
    if not admin_identity:
        return {
            "summary": {
                "precheckout_tracked": False,
                "precheckout_count": None,
                "paid_not_registered_count": 0,
                "registered_count": 0,
            },
            "precheckout_visits": [],
            "paid_not_registered": [],
            "registered_clients": [],
            "notes": [
                "Client pre-checkout visits are not currently persisted in a client-specific table, so this section is not available yet.",
            ],
        }

    completed_jobs_prefetch = Prefetch(
        "user__meal_plan_generation_jobs",
        queryset=ClientMealPlanGenerationJob.objects.filter(status="completed").only(
            "user_id", "day_of_week", "completed_at", "created_at", "status"
        ),
    )
    profiles = list(
        ClientProfile.objects
        .filter(associated_admin=admin_identity)
        .select_related("user")
        .prefetch_related(completed_jobs_prefetch)
        .order_by("-created_at")
    )
    user_ids = [profile.user_id for profile in profiles]
    latest_weight_by_user = {}
    latest_photo_by_user = {}
    weight_30d_counts = {}
    photo_30d_counts = {}
    window_start = now() - timedelta(days=30)

    if user_ids:
        # NOTE: avoid distinct("field") so this works across SQLite/Postgres.
        latest_weight_rows = (
            ClientWeightEntry.objects
            .filter(user_id__in=user_ids)
            .order_by("user_id", "-measured_at", "-created_at")
        )
        for row in latest_weight_rows:
            if row.user_id not in latest_weight_by_user:
                latest_weight_by_user[row.user_id] = row

        latest_photo_rows = (
            ClientProgressPhoto.objects
            .filter(user_id__in=user_ids)
            .order_by("user_id", "-captured_for_date", "-created_at")
        )
        for row in latest_photo_rows:
            if row.user_id not in latest_photo_by_user:
                latest_photo_by_user[row.user_id] = row

        weight_30d_counts = {
            row["user_id"]: int(row["total"])
            for row in (
                ClientWeightEntry.objects
                .filter(user_id__in=user_ids, measured_at__gte=window_start)
                .values("user_id")
                .annotate(total=Count("id"))
            )
        }
        photo_30d_counts = {
            row["user_id"]: int(row["total"])
            for row in (
                ClientProgressPhoto.objects
                .filter(user_id__in=user_ids, created_at__gte=window_start)
                .values("user_id")
                .annotate(total=Count("id"))
            )
        }

    registered_rows = []
    registered_email_set = set()
    for profile in profiles:
        user = profile.user
        user_id = user.id
        email = (getattr(user, "email", "") or "").strip()
        if email:
            registered_email_set.add(email.lower())
        jobs = list(user.meal_plan_generation_jobs.all())
        generator_days = _sorted_days([job.day_of_week for job in jobs if job.day_of_week])
        latest_job_dt = None
        for job in jobs:
            ts = job.completed_at or job.created_at
            if ts and (latest_job_dt is None or ts > latest_job_dt):
                latest_job_dt = ts
        questionnaire = _questionnaire_snapshot(user)
        latest_weight = latest_weight_by_user.get(user_id)
        latest_photo = latest_photo_by_user.get(user_id)
        registered_rows.append(
            {
                "client_user_id": user_id,
                "email": email,
                "offer_code": profile.offer_code,
                "billing_cycle": profile.billing_cycle or "",
                "sale_channel": profile.sale_channel or "",
                "includes_food_plan": bool(profile.includes_food_plan),
                "includes_coaching": bool(profile.includes_coaching),
                "is_active": bool(profile.is_active),
                "created_at": _iso(profile.created_at),
                "questionnaire_status": questionnaire["status"],
                "questionnaire_completed_at": questionnaire["completed_at"],
                "food_generator_used": bool(generator_days),
                "food_generator_days": generator_days,
                "food_generator_last_used_at": _iso(latest_job_dt),
                "latest_weight_value": float(latest_weight.weight_value) if latest_weight else None,
                "latest_weight_unit": latest_weight.unit if latest_weight else "",
                "latest_weight_measured_at": _iso(latest_weight.measured_at) if latest_weight else None,
                "latest_photo_captured_for_date": (
                    latest_photo.captured_for_date.isoformat() if latest_photo else None
                ),
                "latest_photo_uploaded_at": _iso(latest_photo.created_at) if latest_photo else None,
                "weight_entries_last_30_days": int(weight_30d_counts.get(user_id, 0)),
                "photo_uploads_last_30_days": int(photo_30d_counts.get(user_id, 0)),
            }
        )

    paid_pending_qs = (
        ClientPendingSignup.objects
        .filter(admin=admin_identity)
        .order_by("-created_at")
    )
    paid_pending_rows = []
    for pending in paid_pending_qs:
        email = (pending.email or "").strip()
        if email and email.lower() in registered_email_set:
            continue
        paid_pending_rows.append(
            {
                "email": email,
                "offer_code": pending.offer_code,
                "billing_cycle": pending.billing_cycle or "",
                "sale_channel": pending.sale_channel or "",
                "trial_days": int(pending.trial_days or 0),
                "amount_cents": int(pending.amount_cents or 0),
                "includes_food_plan": bool(pending.includes_food_plan),
                "includes_coaching": bool(pending.includes_coaching),
                "registration_link_printed_at": _iso(pending.registration_link_printed_at),
                "created_at": _iso(pending.created_at),
                "questionnaire_status": "not_registered",
                "food_generator_used": False,
                "food_generator_days": [],
            }
        )

    return {
        "summary": {
            "precheckout_tracked": False,
            "precheckout_count": None,
            "paid_not_registered_count": len(paid_pending_rows),
            "registered_count": len(registered_rows),
        },
        "precheckout_visits": [],
        "paid_not_registered": paid_pending_rows,
        "registered_clients": registered_rows,
        "notes": [
            "Client pre-checkout visits are not currently persisted yet. Paid/not-registered and registered client activity is shown from existing records.",
        ],
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
        admin_identity = AdminIdentity.objects.filter(admin_email=user.email).first()

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

        try:
            client_funnel = _build_client_funnel_payload(admin_identity)
        except Exception as exc:
            client_funnel = {
                "summary": {
                    "precheckout_tracked": False,
                    "precheckout_count": None,
                    "paid_not_registered_count": 0,
                    "registered_count": 0,
                },
                "precheckout_visits": [],
                "paid_not_registered": [],
                "registered_clients": [],
                "notes": [
                    "Client activity is temporarily unavailable.",
                    f"Dashboard fallback activated: {exc}" if settings.DEBUG else "Please retry in a moment.",
                ],
            }

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
            "client_funnel": client_funnel,
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
