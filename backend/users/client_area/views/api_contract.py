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
        "error_code": code,
    }
    if details is not None:
        payload["error"]["details"] = details
    return Response(payload, status=http_status)


def require_client(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return error("UNAUTHENTICATED", "Authentication credentials were not provided.", http_status=401)
    if getattr(user, "role", None) != "client":
        return error("FORBIDDEN", "Not authorized as client.", http_status=403)
    return None
