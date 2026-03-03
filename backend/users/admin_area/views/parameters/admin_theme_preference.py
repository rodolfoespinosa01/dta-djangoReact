from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from users.admin_area.models import AdminIdentity
from users.admin_area.views.api_contract import error, ok, require_admin

ALLOWED_THEMES = {"dark", "light"}
DEFAULT_THEME = "light"


def _identity_for_request_user(user):
    identity, _ = AdminIdentity.objects.get_or_create(admin_email=getattr(user, "email", ""))
    return identity


def _normalized_theme(value):
    theme = str(value or "").strip().lower()
    if theme not in ALLOWED_THEMES:
        return DEFAULT_THEME
    return theme


@api_view(["GET", "PUT"])
@permission_classes([IsAuthenticated])
def admin_theme_preference(request):
    auth_error = require_admin(request)
    if auth_error:
        return auth_error

    identity = _identity_for_request_user(request.user)

    if request.method == "GET":
        return ok(
            {
                "theme": _normalized_theme(getattr(identity, "marketing_theme", "") or DEFAULT_THEME),
            }
        )

    payload = request.data or {}
    requested_theme = str(payload.get("theme") or "").strip().lower()
    if requested_theme not in ALLOWED_THEMES:
        return error(
            code="INVALID_THEME",
            message="Theme must be one of: dark, light.",
            http_status=400,
        )

    identity.marketing_theme = requested_theme
    identity.save(update_fields=["marketing_theme"])

    return ok(
        {
            "message": "Theme preference saved.",
            "theme": requested_theme,
        }
    )
