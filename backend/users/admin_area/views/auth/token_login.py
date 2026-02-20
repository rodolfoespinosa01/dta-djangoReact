# backend/users/admin_area/views/auth/token_login.py
from rest_framework_simplejwt.views import TokenObtainPairView as BaseTokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer as BaseTokenObtainPairSerializer
from users.admin_area.models import Profile
from django.contrib.auth import get_user_model
from rest_framework.exceptions import AuthenticationFailed, NotFound
from users.admin_area.views.api_contract import error

class TokenObtainPairSerializer(BaseTokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email'] = user.email
        token['role'] = getattr(user, 'role', None)
        token['subscription_status'] = getattr(user, 'subscription_status', None)
        try:
            current_profile = user.profiles.get(is_active=True)
            token['is_canceled'] = current_profile.is_canceled
        except Profile.DoesNotExist:
            token['is_canceled'] = True
        return token

    def validate(self, attrs):
        User = get_user_model()
        username = attrs.get('username')
        password = attrs.get('password')

        # look up account
        try:
            user = User.objects.get(**{User.USERNAME_FIELD: username})
        except User.DoesNotExist:
            # 404 → "no account found"
            raise NotFound(
                detail=error(
                    code="USER_NOT_FOUND",
                    message="No account found with that email.",
                    http_status=404,
                    legacy_error_code="USER_NOT_FOUND",
                ).data
            )

        if not user.is_active:
            raise AuthenticationFailed(
                detail=error(
                    code="INACTIVE",
                    message="This account is inactive.",
                    http_status=401,
                    legacy_error_code="INACTIVE",
                ).data
            )

        if not user.check_password(password):
            # 401 → "wrong password"
            raise AuthenticationFailed(
                detail=error(
                    code="WRONG_PASSWORD",
                    message="Account found, but the password is incorrect.",
                    http_status=401,
                    legacy_error_code="WRONG_PASSWORD",
                ).data
            )

        # OK → mint tokens (skip parent validate so we keep our flow)
        refresh = self.get_token(user)
        return {
            "ok": True,
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "email": user.email,
            "role": getattr(user, 'role', None),
            "subscription_status": getattr(user, 'subscription_status', None),
            "is_canceled": refresh.get('is_canceled', True),
        }

class TokenObtainPairView(BaseTokenObtainPairView):
    serializer_class = TokenObtainPairSerializer
