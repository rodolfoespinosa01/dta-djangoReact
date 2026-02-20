from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model
from rest_framework.exceptions import AuthenticationFailed, NotFound, PermissionDenied
from users.superadmin_area.views.api_contract import error


class SuperAdminTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["is_superuser"] = user.is_superuser
        token["role"] = "superadmin"
        return token

    def validate(self, attrs):
        User = get_user_model()
        username = attrs.get("username")
        password = attrs.get("password")

        try:
            user = User.objects.get(**{User.USERNAME_FIELD: username})
        except User.DoesNotExist:
            raise NotFound(
                detail=error(
                    code="USER_NOT_FOUND",
                    message="No account found with that username.",
                    http_status=404,
                ).data
            )

        if not user.is_active:
            raise AuthenticationFailed(
                detail=error(
                    code="INACTIVE",
                    message="This account is inactive.",
                    http_status=401,
                ).data
            )

        if not user.check_password(password):
            raise AuthenticationFailed(
                detail=error(
                    code="WRONG_PASSWORD",
                    message="Account found, but the password is incorrect.",
                    http_status=401,
                ).data
            )
        
        if not user.is_superuser:
            raise PermissionDenied(
                detail=error(
                    code="FORBIDDEN",
                    message="Not authorized as SuperAdmin.",
                    http_status=403,
                ).data
            )

        refresh = self.get_token(user)
        return {
            "ok": True,
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "username": user.username,
            "email": user.email,
            "role": "superadmin",
        }


class SuperAdminTokenObtainPairView(TokenObtainPairView):
    serializer_class = SuperAdminTokenObtainPairSerializer
