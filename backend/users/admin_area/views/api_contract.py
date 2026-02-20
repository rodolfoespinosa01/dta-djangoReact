from rest_framework import status
from rest_framework.response import Response


def ok(data=None, http_status=status.HTTP_200_OK):
    payload = {"ok": True}
    if data:
        payload.update(data)
    return Response(payload, status=http_status)


def error(
    code,
    message,
    http_status=status.HTTP_400_BAD_REQUEST,
    details=None,
    legacy_error_code=None,
    extra=None,
):
    payload = {
        "ok": False,
        "error": {
            "code": code,
            "message": message,
        },
        # Backward compatibility for existing frontend extractors.
        "error_code": legacy_error_code or code,
    }
    if details is not None:
        payload["error"]["details"] = details
    if isinstance(extra, dict):
        payload.update(extra)
    return Response(payload, status=http_status)


def require_admin(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return error(
            code="UNAUTHENTICATED",
            message="Authentication credentials were not provided.",
            http_status=status.HTTP_401_UNAUTHORIZED,
        )
    if getattr(user, "role", None) != "admin":
        return error(
            code="FORBIDDEN",
            message="Not authorized as admin.",
            http_status=status.HTTP_403_FORBIDDEN,
        )
    return None
