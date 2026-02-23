from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework.response import Response

from core.services.google_oauth import verify_google_id_token
from users.admin_area.views.api_contract import error
from users.admin_area.views.auth.token_login import TokenObtainPairSerializer


@api_view(["POST"])
@permission_classes([AllowAny])
def admin_google_login(request):
    payload = request.data or {}
    credential = (payload.get("credential") or "").strip()
    if not credential:
        return error(code="MISSING_CREDENTIAL", message="Missing Google credential.", http_status=400)

    try:
        google_payload = verify_google_id_token(credential)
    except RuntimeError as exc:
        return error(code="GOOGLE_CONFIG_ERROR", message=str(exc), http_status=500)
    except ValueError as exc:
        return error(code="INVALID_GOOGLE_TOKEN", message=str(exc), http_status=401)

    email = (google_payload.get("email") or "").strip().lower()
    email_verified = bool(google_payload.get("email_verified"))
    if not email or not email_verified:
        return error(code="GOOGLE_EMAIL_UNVERIFIED", message="Google account email is missing or not verified.", http_status=401)

    User = get_user_model()
    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        return error(code="USER_NOT_FOUND", message="No admin account found with that Google email.", http_status=404)

    if not user.is_active:
        return error(code="INACTIVE", message="This account is inactive.", http_status=401)
    if getattr(user, "role", None) != "admin":
        return error(code="WRONG_ROLE", message="This is not an admin account.", http_status=401)

    refresh = TokenObtainPairSerializer.get_token(user)
    return Response(
        {
            "ok": True,
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "email": user.email,
            "role": getattr(user, "role", None),
            "subscription_status": getattr(user, "subscription_status", None),
            "is_canceled": refresh.get("is_canceled", True),
        },
        status=status.HTTP_200_OK,
    )
