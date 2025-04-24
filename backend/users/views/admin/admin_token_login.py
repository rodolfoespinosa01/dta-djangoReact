from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from users.models.custom_user import CustomUser

# 🔐 Custom serializer to enrich the JWT payload with extra claims
class AdminTokenObtainPairSerializer(TokenObtainPairSerializer):

    @classmethod
    def get_token(cls, user):
        # 🔑 Start with the base token from the parent class
        token = super().get_token(user)

        # ➕ Add custom claims to the token payload
        token['email'] = user.email
        token['role'] = user.role
        token['subscription_status'] = user.subscription_status

        return token

    def validate(self, attrs):
        # Run default validation logic (checks username & password)
        data = super().validate(attrs)
        return data


# 🎯 Custom login view using the above serializer
class AdminTokenObtainPairView(TokenObtainPairView):
    serializer_class = AdminTokenObtainPairSerializer
