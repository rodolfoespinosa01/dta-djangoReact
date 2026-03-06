from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from users.client_area.models import ClientProfile
from users.client_area.views.api_contract import error, ok, require_client
from core.services.theme_preferences import ALLOWED_THEMES, DEFAULT_THEME, normalize_theme


@api_view(["GET", "PUT"])
@permission_classes([IsAuthenticated])
def client_theme_preference(request):
    auth_error = require_client(request)
    if auth_error:
        return auth_error

    profile = ClientProfile.objects.filter(user=request.user).first()
    if not profile:
        return error("CLIENT_PROFILE_NOT_FOUND", "Client profile not found.", http_status=404)

    if request.method == "GET":
        return ok({"theme": normalize_theme(getattr(profile, "theme_preference", "") or DEFAULT_THEME)})

    payload = request.data or {}
    requested_theme = str(payload.get("theme") or "").strip().lower()
    if requested_theme not in ALLOWED_THEMES:
        return error(
            code="INVALID_THEME",
            message="Theme must be one of: dark, light.",
            http_status=400,
        )

    profile.theme_preference = requested_theme
    profile.save(update_fields=["theme_preference", "updated_at"])

    return ok(
        {
            "message": "Theme preference saved.",
            "theme": requested_theme,
        }
    )
