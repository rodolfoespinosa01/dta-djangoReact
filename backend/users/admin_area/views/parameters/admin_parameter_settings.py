import copy
import re

from django.db import IntegrityError
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from users.admin_area.models import (
    AdminIdentity,
    AdminParameterSettingsChangeLog,
)
from users.admin_area.services.admin_parameter_tables import (
    apply_admin_parameter_payload,
    admin_parameter_state,
    ensure_admin_parameter_tables,
    get_admin_parameter_payload,
    reset_admin_parameter_payload_to_defaults,
)
from users.admin_area.views.api_contract import error, ok, require_admin


SUBDOMAIN_SLUG_RE = re.compile(r"^[a-z]+(?:-[a-z]+)*$")
RESERVED_SUBDOMAIN_SLUGS = {
    "www",
    "admin",
    "api",
    "app",
    "support",
    "mail",
    "static",
}


def _identity_for_request_user(user):
    return AdminIdentity.objects.get_or_create(admin_email=getattr(user, "email", ""))[0]


def _settings_for_request_user(user):
    identity = _identity_for_request_user(user)
    return ensure_admin_parameter_tables(identity)


def _subdomain_status(identity):
    slug = (identity.subdomain_slug or "").strip() or None
    return {
        "slug": slug,
        "locked": bool(slug and identity.subdomain_locked_at),
        "locked_at": identity.subdomain_locked_at,
        "preview_url": f"{slug}.lvh.me:3000" if slug else None,
        "production_url": f"{slug}.dtameals.com" if slug else None,
    }


def _validate_subdomain_slug(raw_slug):
    if raw_slug is None:
        return None, "Subdomain is required."
    slug = str(raw_slug).strip().lower()
    if not slug:
        return None, "Subdomain is required."
    if " " in slug:
        return None, "Subdomain cannot contain spaces."
    if len(slug) < 3 or len(slug) > 40:
        return None, "Subdomain must be between 3 and 40 characters."
    if slug in RESERVED_SUBDOMAIN_SLUGS:
        return None, "That subdomain is reserved. Please choose another."
    if not SUBDOMAIN_SLUG_RE.fullmatch(slug):
        return None, "Use only letters and hyphens (no numbers, spaces, underscores, or leading/trailing hyphens)."
    return slug, None


def _set_subdomain_once(identity, raw_slug):
    if identity.subdomain_slug:
        existing = (identity.subdomain_slug or "").strip().lower()
        incoming, err = _validate_subdomain_slug(raw_slug)
        if err:
            return None, err
        if incoming != existing:
            return None, "Subdomain is locked and can only be set once."
        return identity.subdomain_slug, None

    slug, err = _validate_subdomain_slug(raw_slug)
    if err:
        return None, err

    identity.subdomain_slug = slug
    identity.subdomain_locked_at = timezone.now()
    try:
        identity.save(update_fields=["subdomain_slug", "subdomain_locked_at"])
    except IntegrityError:
        return None, "That subdomain is already taken. Please choose another."
    return identity.subdomain_slug, None


def _json_diff_paths(before, after, prefix=""):
    paths = []
    if type(before) is not type(after):
        return [prefix or "$"]

    if isinstance(before, dict):
        keys = sorted(set(before.keys()) | set(after.keys()))
        for key in keys:
            next_prefix = f"{prefix}.{key}" if prefix else str(key)
            if key not in before or key not in after:
                paths.append(next_prefix)
                continue
            paths.extend(_json_diff_paths(before[key], after[key], next_prefix))
        return paths

    if isinstance(before, list):
        if len(before) != len(after):
            return [prefix or "$"]
        for idx, (before_item, after_item) in enumerate(zip(before, after)):
            next_prefix = f"{prefix}[{idx}]" if prefix else f"[{idx}]"
            paths.extend(_json_diff_paths(before_item, after_item, next_prefix))
        return paths

    if before != after:
        return [prefix or "$"]
    return []


def _record_change_log(*, admin_identity, action, before_json, after_json):
    changed_paths = _json_diff_paths(before_json, after_json)
    if not changed_paths:
        return []

    AdminParameterSettingsChangeLog.objects.create(
        admin=admin_identity,
        action=action,
        changed_paths=changed_paths,
        before_json=before_json,
        after_json=after_json,
    )
    return changed_paths


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def parameter_settings_status(request):
    auth_error = require_admin(request)
    if auth_error:
        return auth_error

    identity = _identity_for_request_user(request.user)
    state = ensure_admin_parameter_tables(identity)
    initialized = bool(state.get("initialized"))
    subdomain = _subdomain_status(identity)
    setup_completed = initialized and subdomain["locked"]

    return ok(
        {
            "parameter_settings": {
                "exists": bool(state.get("exists")),
                "initialized": initialized,
                "setup_completed": setup_completed,
                "defaults_version_applied": state.get("defaults_version_applied"),
                "updated_at": state.get("updated_at"),
            }
            ,
            "subdomain": subdomain,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def parameter_settings_use_defaults(request):
    auth_error = require_admin(request)
    if auth_error:
        return auth_error

    identity = _identity_for_request_user(request.user)
    state = ensure_admin_parameter_tables(identity)
    subdomain_slug, subdomain_error = _set_subdomain_once(identity, (request.data or {}).get("subdomain_slug"))
    if subdomain_error:
        return error(
            code="INVALID_SUBDOMAIN_SLUG",
            message=subdomain_error,
            http_status=400,
        )
    before_json = copy.deepcopy(get_admin_parameter_payload(identity))
    state = reset_admin_parameter_payload_to_defaults(
        identity,
        version=state.get("defaults_version_applied") or "v1",
    )
    after_json = copy.deepcopy(get_admin_parameter_payload(identity))
    changed_paths = _record_change_log(
        admin_identity=identity,
        action="use_defaults",
        before_json=before_json,
        after_json=after_json,
    )

    return ok(
        {
            "message": "Default admin parameter settings applied.",
            "parameter_settings": {
                "initialized": bool(state.get("initialized")),
                "setup_completed": True,
                "defaults_version_applied": state.get("defaults_version_applied"),
                "updated_at": state.get("updated_at"),
                "changed_paths_count": len(changed_paths),
            },
            "subdomain": _subdomain_status(identity),
        }
    )


@api_view(["GET", "PUT"])
@permission_classes([IsAuthenticated])
def parameter_settings_detail(request):
    auth_error = require_admin(request)
    if auth_error:
        return auth_error

    identity = _identity_for_request_user(request.user)
    state = ensure_admin_parameter_tables(identity)

    if request.method == "GET":
        parameters_json = get_admin_parameter_payload(identity)
        return ok(
            {
                "parameter_settings": {
                    "initialized": bool(state.get("initialized")),
                    "setup_completed": bool(state.get("initialized") and identity.subdomain_slug and identity.subdomain_locked_at),
                    "defaults_version_applied": state.get("defaults_version_applied"),
                    "created_at": state.get("created_at"),
                    "updated_at": state.get("updated_at"),
                    "parameters_json": parameters_json,
                },
                "subdomain": _subdomain_status(identity),
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

    requested_initialized = bool(payload.get("initialized", True))
    if requested_initialized:
        _, subdomain_error = _set_subdomain_once(identity, payload.get("subdomain_slug"))
        if subdomain_error:
            return error(
                code="INVALID_SUBDOMAIN_SLUG",
                message=subdomain_error,
                http_status=400,
            )

    before_json = copy.deepcopy(get_admin_parameter_payload(identity))
    state = apply_admin_parameter_payload(identity, params, initialized=requested_initialized)
    after_json = copy.deepcopy(get_admin_parameter_payload(identity))
    changed_paths = _record_change_log(
        admin_identity=identity,
        action="manual_save",
        before_json=before_json,
        after_json=after_json,
    )

    return ok(
        {
            "message": "Admin parameter settings saved.",
            "parameter_settings": {
                "initialized": bool(state.get("initialized")),
                "setup_completed": bool(state.get("initialized") and identity.subdomain_slug and identity.subdomain_locked_at),
                "defaults_version_applied": state.get("defaults_version_applied"),
                "updated_at": state.get("updated_at"),
                "parameters_json": after_json,
                "changed_paths_count": len(changed_paths),
                "changed_paths_preview": changed_paths[:20],
            },
            "subdomain": _subdomain_status(identity),
        }
    )
