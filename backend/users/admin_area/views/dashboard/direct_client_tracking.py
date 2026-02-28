from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from users.admin_area.models import AdminIdentity
from users.admin_area.views.api_contract import error, ok, require_admin
from users.client_area.models import ClientProfile, ClientProgressPhoto, ClientWeightEntry


def _serialize_photo(request, row: ClientProgressPhoto):
    file_url = row.file.url if row.file else ""
    if file_url and not file_url.startswith("http"):
        file_url = request.build_absolute_uri(file_url)
    return {
        "id": row.id,
        "captured_for_date": row.captured_for_date.isoformat(),
        "file_url": file_url,
        "notes": row.notes or "",
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _serialize_weight(row: ClientWeightEntry):
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


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_client_tracking(request, user_id: int):
    auth_error = require_admin(request)
    if auth_error:
        return auth_error

    admin_identity = AdminIdentity.objects.filter(admin_email=request.user.email).first()
    if not admin_identity:
        return error(
            code="ADMIN_IDENTITY_NOT_FOUND",
            message="Admin identity not found.",
            http_status=404,
        )

    profile = (
        ClientProfile.objects
        .filter(user_id=user_id, associated_admin=admin_identity)
        .select_related("user")
        .first()
    )
    if not profile:
        return error(
            code="CLIENT_NOT_FOUND",
            message="Client not found for this admin.",
            http_status=404,
        )

    photos = list(
        ClientProgressPhoto.objects
        .filter(user_id=user_id)
        .order_by("-captured_for_date", "-created_at")[:120]
    )
    weights = list(
        ClientWeightEntry.objects
        .filter(user_id=user_id)
        .order_by("-measured_at", "-created_at")[:180]
    )

    return ok(
        {
            "client": {
                "client_user_id": profile.user_id,
                "email": profile.user.email,
                "offer_code": profile.offer_code,
                "billing_cycle": profile.billing_cycle or "",
                "is_active": bool(profile.is_active),
                "created_at": profile.created_at.isoformat() if profile.created_at else None,
            },
            "tracking": {
                "photos": [_serialize_photo(request, row) for row in photos],
                "weights": [_serialize_weight(row) for row in weights],
                "summary": {
                    "photo_count": len(photos),
                    "weight_count": len(weights),
                },
            },
        }
    )
