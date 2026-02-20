from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.models import CustomUser

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


def _build_day_series(events, now):
    start = now - timedelta(hours=23)
    buckets = []
    labels = []

    for i in range(24):
        slot = start + timedelta(hours=i)
        buckets.append({"start": slot, "end": slot + timedelta(hours=1), "total_cents": 0})
        labels.append(slot.strftime("%H:00"))

    filtered = []
    for event in events:
        ts = event["timestamp"]
        if ts < start or ts > now:
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
    return filtered, points


def _build_day_span_series(events, now, days):
    start_of_today = timezone.localtime(now).replace(hour=0, minute=0, second=0, microsecond=0)
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
        if ts < start or ts > now:
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
    return filtered, points


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def analytics(request):
    if not request.user.is_superuser:
        return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

    period = (request.query_params.get("period") or "day").lower()
    if period not in VALID_PERIODS:
        return Response(
            {"error": "Invalid period. Use one of: day, week, month."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    now = timezone.now()
    events = list(_iter_paid_events())

    if period == "day":
        filtered_events, points = _build_day_series(events, now)
    elif period == "week":
        filtered_events, points = _build_day_span_series(events, now, 7)
    else:
        filtered_events, points = _build_day_span_series(events, now, 30)

    total_cents = sum(event["amount_cents"] for event in filtered_events)

    return Response(
        {
            "period": period,
            "total_revenue": float(Decimal(total_cents) / Decimal("100")),
            "total_revenue_cents": total_cents,
            "transactions": len(filtered_events),
            "points": points,
        },
        status=status.HTTP_200_OK,
    )
