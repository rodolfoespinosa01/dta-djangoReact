from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation

from django.db import IntegrityError
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from users.client_area.models import ClientProgressPhoto, ClientWeightEntry
from users.client_area.views.api_contract import error, ok, require_client


MAX_MONTHLY_PHOTOS = 30
MAX_FILE_BYTES = 12 * 1024 * 1024  # 12MB


def _month_bounds(day_value: date):
    first = day_value.replace(day=1)
    if first.month == 12:
        next_month = first.replace(year=first.year + 1, month=1, day=1)
    else:
        next_month = first.replace(month=first.month + 1, day=1)
    last = next_month - timedelta(days=1)
    return first, last


def _parse_date(value: str | None):
    raw = str(value or "").strip()
    if not raw:
        return timezone.localdate()
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _parse_time(value: str | None):
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parts = raw.split(":")
        if len(parts) < 2:
            return None
        hh = int(parts[0])
        mm = int(parts[1])
        if hh < 0 or hh > 23 or mm < 0 or mm > 59:
            return None
        return time(hour=hh, minute=mm)
    except Exception:
        return None


def _as_bool(value, default=True):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _serialize_row(request, row: ClientProgressPhoto):
    file_url = row.file.url if row.file else ""
    if file_url and not file_url.startswith("http"):
        file_url = request.build_absolute_uri(file_url)
    return {
        "id": row.id,
        "captured_for_date": row.captured_for_date.isoformat(),
        "same_position": bool(row.same_position),
        "same_lighting": bool(row.same_lighting),
        "same_time_of_day": bool(row.same_time_of_day),
        "notes": row.notes or "",
        "file_url": file_url,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _monthly_stats(user, day_value: date):
    start, end = _month_bounds(day_value)
    count = ClientProgressPhoto.objects.filter(
        user=user,
        captured_for_date__gte=start,
        captured_for_date__lte=end,
    ).count()
    return {
        "month": start.strftime("%Y-%m"),
        "month_start": start.isoformat(),
        "month_end": end.isoformat(),
        "monthly_count": count,
        "monthly_limit": MAX_MONTHLY_PHOTOS,
        "monthly_remaining": max(0, MAX_MONTHLY_PHOTOS - count),
    }


def _serialize_weight_row(row: ClientWeightEntry):
    local_dt = timezone.localtime(row.measured_at)
    return {
        "id": row.id,
        "measured_at": local_dt.isoformat(),
        "measured_date": local_dt.date().isoformat(),
        "measured_time": local_dt.strftime("%H:%M"),
        "weight_value": float(row.weight_value),
        "unit": row.unit,
        "notes": row.notes or "",
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def client_progress_photos(request):
    auth_error = require_client(request)
    if auth_error:
        return auth_error

    if request.method == "GET":
        today = timezone.localdate()
        stats = _monthly_stats(request.user, today)
        rows = ClientProgressPhoto.objects.filter(user=request.user).order_by("-captured_for_date", "-created_at")[:90]
        return ok(
            {
                "photos": [_serialize_row(request, row) for row in rows],
                "tracking": {
                    **stats,
                    "can_upload_today": not ClientProgressPhoto.objects.filter(
                        user=request.user,
                        captured_for_date=today,
                    ).exists(),
                    "recommended_cadence": "weekly",
                    "max_frequency": "daily",
                },
            }
        )

    upload = request.FILES.get("photo")
    if not upload:
        return error("MISSING_PHOTO", "A photo file is required.", http_status=400)

    content_type = str(getattr(upload, "content_type", "") or "").lower()
    if not content_type.startswith("image/"):
        return error("INVALID_FILE_TYPE", "Only image uploads are supported.", http_status=400)
    if int(getattr(upload, "size", 0) or 0) > MAX_FILE_BYTES:
        return error("FILE_TOO_LARGE", "Photo exceeds max size (12MB).", http_status=400)

    captured_for_date = _parse_date(request.data.get("captured_for_date"))
    if captured_for_date is None:
        return error("INVALID_DATE", "captured_for_date must be YYYY-MM-DD.", http_status=400)
    if captured_for_date > timezone.localdate():
        return error("INVALID_DATE", "captured_for_date cannot be in the future.", http_status=400)

    if ClientProgressPhoto.objects.filter(user=request.user, captured_for_date=captured_for_date).exists():
        return error("DAILY_LIMIT_REACHED", "You already uploaded a progress photo for this date.", http_status=409)

    stats = _monthly_stats(request.user, captured_for_date)
    if stats["monthly_count"] >= MAX_MONTHLY_PHOTOS:
        return error("MONTHLY_LIMIT_REACHED", "Monthly upload limit reached (30 photos).", http_status=409, details=stats)

    row = ClientProgressPhoto(
        user=request.user,
        file=upload,
        captured_for_date=captured_for_date,
        same_position=_as_bool(request.data.get("same_position"), default=True),
        same_lighting=_as_bool(request.data.get("same_lighting"), default=True),
        same_time_of_day=_as_bool(request.data.get("same_time_of_day"), default=True),
        notes=str(request.data.get("notes") or "").strip()[:300],
    )
    try:
        row.save()
    except IntegrityError:
        return error("DAILY_LIMIT_REACHED", "You already uploaded a progress photo for this date.", http_status=409)

    created_weight = None
    raw_weight_value = str(request.data.get("weight_value") or "").strip()
    if raw_weight_value:
        raw_measured_time = str(request.data.get("measured_time") or "").strip()
        measured_time = _parse_time(raw_measured_time)
        if measured_time is None:
            return error("INVALID_TIME", "measured_time must be HH:MM (24-hour) when weight is provided.", http_status=400)
        try:
            weight_value = Decimal(raw_weight_value)
        except (InvalidOperation, ValueError):
            return error("INVALID_WEIGHT", "weight_value must be a valid number.", http_status=400)
        if weight_value <= 0:
            return error("INVALID_WEIGHT", "weight_value must be greater than 0.", http_status=400)

        unit = str(request.data.get("weight_unit") or "lbs").strip().lower()
        if unit not in {"lbs", "kg"}:
            return error("INVALID_UNIT", "weight_unit must be lbs or kg.", http_status=400)

        local_tz = timezone.get_current_timezone()
        measured_at = timezone.make_aware(datetime.combine(captured_for_date, measured_time), local_tz)
        if measured_at > timezone.now() + timedelta(minutes=5):
            return error("INVALID_TIMESTAMP", "Measured time cannot be in the future.", http_status=400)

        created_weight = ClientWeightEntry.objects.create(
            user=request.user,
            measured_at=measured_at,
            weight_value=weight_value,
            unit=unit,
            notes=str(request.data.get("weight_notes") or "").strip()[:160],
        )

    new_stats = _monthly_stats(request.user, captured_for_date)
    return ok(
        {
            "message": "Progress photo uploaded.",
            "photo": _serialize_row(request, row),
            "weight": _serialize_weight_row(created_weight) if created_weight else None,
            "tracking": {
                **new_stats,
                "recommended_cadence": "weekly",
                "max_frequency": "daily",
            },
        },
        http_status=201,
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def client_weight_entries(request):
    auth_error = require_client(request)
    if auth_error:
        return auth_error

    if request.method == "GET":
        rows = ClientWeightEntry.objects.filter(user=request.user).order_by("-measured_at", "-created_at")[:180]
        latest = rows[0] if rows else None
        return ok(
            {
                "weights": [_serialize_weight_row(row) for row in rows],
                "summary": {
                    "latest_weight": float(latest.weight_value) if latest else None,
                    "latest_unit": latest.unit if latest else None,
                    "latest_measured_at": timezone.localtime(latest.measured_at).isoformat() if latest else None,
                    "entry_count": len(rows),
                },
            }
        )

    measured_date = _parse_date(request.data.get("measured_date"))
    if measured_date is None:
        return error("INVALID_DATE", "measured_date must be YYYY-MM-DD.", http_status=400)
    measured_time = _parse_time(request.data.get("measured_time"))
    if measured_time is None:
        return error("INVALID_TIME", "measured_time must be HH:MM (24-hour).", http_status=400)

    try:
        weight_value = Decimal(str(request.data.get("weight_value") or "").strip())
    except (InvalidOperation, ValueError):
        return error("INVALID_WEIGHT", "weight_value must be a valid number.", http_status=400)
    if weight_value <= 0:
        return error("INVALID_WEIGHT", "weight_value must be greater than 0.", http_status=400)

    unit = str(request.data.get("unit") or "lbs").strip().lower()
    if unit not in {"lbs", "kg"}:
        return error("INVALID_UNIT", "unit must be lbs or kg.", http_status=400)

    local_tz = timezone.get_current_timezone()
    measured_at = timezone.make_aware(datetime.combine(measured_date, measured_time), local_tz)
    if measured_at > timezone.now() + timedelta(minutes=5):
        return error("INVALID_TIMESTAMP", "Measured time cannot be in the future.", http_status=400)

    row = ClientWeightEntry(
        user=request.user,
        measured_at=measured_at,
        weight_value=weight_value,
        unit=unit,
        notes=str(request.data.get("notes") or "").strip()[:160],
    )
    try:
        row.save()
    except IntegrityError as exc:
        return error("WEIGHT_SAVE_FAILED", f"Could not save weight entry: {exc}", http_status=400)

    return ok(
        {
            "message": "Weight entry saved.",
            "weight": _serialize_weight_row(row),
        },
        http_status=201,
    )
