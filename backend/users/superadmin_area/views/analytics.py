from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from core.models import CustomUser
from users.superadmin_area.serializers import SuperAdminAnalyticsPayloadSerializer
from .api_contract import error, ok, require_superadmin

VALID_PERIODS = {"day", "week", "month"}


def _iter_paid_events():
    seen_transactions = set()

    admins = CustomUser.objects.filter(role="admin").prefetch_related("profiles__plan")
    for admin in admins:
        for profile in admin.profiles.all():
            if not profile.plan or profile.plan.price_cents <= 0 or profile.is_trial:
                continue

            tx_id = (profile.stripe_transaction_id or "").strip()
            dedupe_key = tx_id or str(profile.profile_id)
            if dedupe_key in seen_transactions:
                continue

            seen_transactions.add(dedupe_key)
            yield {
                "amount_cents": profile.plan.price_cents,
                "timestamp": profile.created_at,
            }


def _start_of_today(now):
    local_now = timezone.localtime(now)
    return local_now.replace(hour=0, minute=0, second=0, microsecond=0)


def _build_day_series(events, now):
    start = _start_of_today(now)
    local_now = timezone.localtime(now)
    buckets = []
    labels = []

    for i in range(24):
        slot = start + timedelta(hours=i)
        buckets.append({"start": slot, "end": slot + timedelta(hours=1), "total_cents": 0})
        labels.append(slot.strftime("%H:00"))

    filtered = []
    for event in events:
        ts = timezone.localtime(event["timestamp"])
        if ts < start or ts > local_now:
            continue
        filtered.append(event)
        idx = int((ts - start).total_seconds() // 3600)
        idx = max(0, min(23, idx))
        buckets[idx]["total_cents"] += event["amount_cents"]

    points = [
        {
            "label": labels[i],
            "amount": float(Decimal(bucket["total_cents"]) / Decimal("100")),
            "amount_cents": bucket["total_cents"],
        }
        for i, bucket in enumerate(buckets)
    ]
    return filtered, points, start, local_now


def _build_day_span_series(events, now, days):
    local_now = timezone.localtime(now)
    start_of_today = _start_of_today(now)
    start = start_of_today - timedelta(days=days - 1)

    buckets = []
    for i in range(days):
        day_start = start + timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        buckets.append({
            "start": day_start,
            "end": day_end,
            "label": day_start.strftime("%b %d"),
            "total_cents": 0,
        })

    filtered = []
    for event in events:
        ts = timezone.localtime(event["timestamp"])
        if ts < start or ts > local_now:
            continue
        filtered.append(event)

        idx = (ts.date() - start.date()).days
        if 0 <= idx < days:
            buckets[idx]["total_cents"] += event["amount_cents"]

    points = [
        {
            "label": bucket["label"],
            "amount": float(Decimal(bucket["total_cents"]) / Decimal("100")),
            "amount_cents": bucket["total_cents"],
        }
        for bucket in buckets
    ]
    return filtered, points, start, local_now


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def analytics(request):
    auth_error = require_superadmin(request)
    if auth_error:
        return auth_error

    period = (request.query_params.get("period") or "day").lower()
    if period not in VALID_PERIODS:
        return error(
            code="INVALID_PERIOD",
            message="Invalid period. Use one of: day, week, month.",
            details={"allowed": sorted(VALID_PERIODS)},
        )

    now = timezone.now()
    events = list(_iter_paid_events())

    if period == "day":
        filtered_events, points, window_start, window_end = _build_day_series(events, now)
        bucket = "hour"
    elif period == "week":
        filtered_events, points, window_start, window_end = _build_day_span_series(events, now, 7)
        bucket = "day"
    else:
        filtered_events, points, window_start, window_end = _build_day_span_series(events, now, 30)
        bucket = "day"

    total_cents = sum(event["amount_cents"] for event in filtered_events)
    payload = {
        "period": period,
        "currency": "USD",
        "total_revenue": float(Decimal(total_cents) / Decimal("100")),
        "total_revenue_cents": total_cents,
        "transactions": len(filtered_events),
        "generated_at": timezone.localtime(now),
        "window": {
            "started_at": window_start,
            "ended_at": window_end,
            "timezone": timezone.get_current_timezone_name(),
            "bucket": bucket,
        },
        "points": points,
    }

    serializer = SuperAdminAnalyticsPayloadSerializer(data=payload)
    if not serializer.is_valid():
        return error(
            code="ANALYTICS_PAYLOAD_INVALID",
            message="SuperAdmin analytics payload validation failed.",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=serializer.errors,
        )
    return ok(serializer.validated_data)
