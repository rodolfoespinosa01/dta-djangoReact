from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from core.services.google_oauth import verify_google_id_token
from users.client_area.views.api_contract import error
from users.client_area.views.token_login import ClientTokenObtainPairSerializer


@api_view(["POST"])
@permission_classes([AllowAny])
def client_google_login(request):
    payload = request.data or {}
    credential = (payload.get("credential") or "").strip()
    if not credential:
        return error("MISSING_CREDENTIAL", "Missing Google credential.", http_status=400)

    try:
        google_payload = verify_google_id_token(credential)
    except RuntimeError as exc:
        return error("GOOGLE_CONFIG_ERROR", str(exc), http_status=500)
    except ValueError as exc:
        return error("INVALID_GOOGLE_TOKEN", str(exc), http_status=401)

    email = (google_payload.get("email") or "").strip().lower()
    email_verified = bool(google_payload.get("email_verified"))
    if not email or not email_verified:
        return error("GOOGLE_EMAIL_UNVERIFIED", "Google account email is missing or not verified.", http_status=401)

    User = get_user_model()
    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        return error("USER_NOT_FOUND", "No client account found with that Google email.", http_status=404)

    if not user.is_active:
        return error("INACTIVE", "This account is inactive.", http_status=401)
    if getattr(user, "role", None) != "client":
        return error("WRONG_ROLE", "This is not a client account.", http_status=401)

    refresh = ClientTokenObtainPairSerializer.get_token(user)
    return Response(
        {
            "ok": True,
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "email": user.email,
            "role": getattr(user, "role", None),
        }
    )

