from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from users.admin_area.configs.admin_parameter_defaults import get_admin_parameter_defaults_v1
from users.admin_area.models import AdminIdentity, AdminParameterSettings
from users.admin_area.views.api_contract import error, ok, require_admin


def _identity_for_request_user(user):
    return AdminIdentity.objects.get_or_create(admin_email=getattr(user, "email", ""))[0]


def _settings_for_request_user(user):
    identity = _identity_for_request_user(user)
    settings_obj, _ = AdminParameterSettings.objects.get_or_create(admin=identity)
    return settings_obj


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def parameter_settings_status(request):
    auth_error = require_admin(request)
    if auth_error:
        return auth_error

    identity = _identity_for_request_user(request.user)
    settings_obj = AdminParameterSettings.objects.filter(admin=identity).first()
    initialized = bool(settings_obj and settings_obj.initialized)

    return ok(
        {
            "parameter_settings": {
                "exists": bool(settings_obj),
                "initialized": initialized,
                "defaults_version_applied": getattr(settings_obj, "defaults_version_applied", None),
                "updated_at": getattr(settings_obj, "updated_at", None),
            }
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def parameter_settings_use_defaults(request):
    auth_error = require_admin(request)
    if auth_error:
        return auth_error

    settings_obj = _settings_for_request_user(request.user)
    defaults = get_admin_parameter_defaults_v1()
    settings_obj.parameters_json = defaults
    settings_obj.defaults_version_applied = defaults.get("version", "v1")
    settings_obj.initialized = True
    settings_obj.save(update_fields=["parameters_json", "defaults_version_applied", "initialized", "updated_at"])

    return ok(
        {
            "message": "Default admin parameter settings applied.",
            "parameter_settings": {
                "initialized": settings_obj.initialized,
                "defaults_version_applied": settings_obj.defaults_version_applied,
                "updated_at": settings_obj.updated_at,
            },
        }
    )


@api_view(["GET", "PUT"])
@permission_classes([IsAuthenticated])
def parameter_settings_detail(request):
    auth_error = require_admin(request)
    if auth_error:
        return auth_error

    settings_obj = _settings_for_request_user(request.user)

    if request.method == "GET":
        return ok(
            {
                "parameter_settings": {
                    "initialized": settings_obj.initialized,
                    "defaults_version_applied": settings_obj.defaults_version_applied,
                    "created_at": settings_obj.created_at,
                    "updated_at": settings_obj.updated_at,
                    "parameters_json": settings_obj.parameters_json,
                }
            }
        )

    payload = request.data or {}
    params = payload.get("parameters_json")
    if not isinstance(params, dict):
        return error(
            code="INVALID_PARAMETERS_JSON",
            message="`parameters_json` must be an object.",
            http_status=400,
        )

    settings_obj.parameters_json = params
    settings_obj.defaults_version_applied = params.get("version") or settings_obj.defaults_version_applied or "v1"
    settings_obj.initialized = bool(payload.get("initialized", True))
    settings_obj.save(update_fields=["parameters_json", "defaults_version_applied", "initialized", "updated_at"])

    return ok(
        {
            "message": "Admin parameter settings saved.",
            "parameter_settings": {
                "initialized": settings_obj.initialized,
                "defaults_version_applied": settings_obj.defaults_version_applied,
                "updated_at": settings_obj.updated_at,
                "parameters_json": settings_obj.parameters_json,
            }
        }
    )

