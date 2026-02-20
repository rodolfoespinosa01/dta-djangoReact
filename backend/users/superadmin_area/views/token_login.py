from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers


class SuperAdminTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["is_superuser"] = user.is_superuser
        token["role"] = "superadmin"
        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        if not self.user.is_superuser:
            raise serializers.ValidationError(
                {
                    "ok": False,
                    "error": {
                        "code": "FORBIDDEN",
                        "message": "Not authorized as SuperAdmin.",
                    },
                }
            )

        data["ok"] = True
        data["username"] = self.user.username
        data["email"] = self.user.email
        data["role"] = "superadmin"
        return data


class SuperAdminTokenObtainPairView(TokenObtainPairView):
    serializer_class = SuperAdminTokenObtainPairSerializer
