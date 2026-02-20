from rest_framework import status
from rest_framework.response import Response


def ok(data=None, http_status=status.HTTP_200_OK):
    payload = {"ok": True}
    if data:
        payload.update(data)
    return Response(payload, status=http_status)


def error(code, message, http_status=status.HTTP_400_BAD_REQUEST, details=None):
    payload = {
        "ok": False,
        "error": {
            "code": code,
            "message": message,
        },
    }
    if details is not None:
        payload["error"]["details"] = details
    return Response(payload, status=http_status)


def require_superadmin(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return error(
            code="UNAUTHENTICATED",
            message="Authentication credentials were not provided.",
            http_status=status.HTTP_401_UNAUTHORIZED,
        )
    if not user.is_superuser:
        return error(
            code="FORBIDDEN",
            message="Not authorized as SuperAdmin.",
            http_status=status.HTTP_403_FORBIDDEN,
        )
    return None
