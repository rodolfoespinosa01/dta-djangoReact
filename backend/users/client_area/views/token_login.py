from django.contrib.auth import get_user_model
from rest_framework.exceptions import AuthenticationFailed, NotFound
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer as BaseTokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView as BaseTokenObtainPairView

from users.client_area.views.api_contract import error

def _is_gmail_email(value):
    email = (value or "").strip().lower()
    return email.endswith("@gmail.com") or email.endswith("@googlemail.com")


class ClientTokenObtainPairSerializer(BaseTokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email
        token["role"] = getattr(user, "role", None)
        return token

    def validate(self, attrs):
        User = get_user_model()
        username = attrs.get("username")
        password = attrs.get("password")

        try:
            user = User.objects.get(**{User.USERNAME_FIELD: username})
        except User.DoesNotExist:
            raise NotFound(detail=error("USER_NOT_FOUND", "No account found with that email.", http_status=404).data)

        if not user.is_active:
            raise AuthenticationFailed(detail=error("INACTIVE", "This account is inactive.", http_status=401).data)

        if getattr(user, "role", None) != "client":
            raise AuthenticationFailed(detail=error("WRONG_ROLE", "This is not a client account.", http_status=401).data)

        if _is_gmail_email(getattr(user, "email", username)):
            raise AuthenticationFailed(detail=error("GOOGLE_REQUIRED", "Gmail accounts must use Google sign-in.", http_status=401).data)

        if not user.check_password(password):
            raise AuthenticationFailed(detail=error("WRONG_PASSWORD", "Password is incorrect.", http_status=401).data)

        refresh = self.get_token(user)
        return {
            "ok": True,
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "email": user.email,
            "role": getattr(user, "role", None),
        }


class ClientTokenObtainPairView(BaseTokenObtainPairView):
    serializer_class = ClientTokenObtainPairSerializer
