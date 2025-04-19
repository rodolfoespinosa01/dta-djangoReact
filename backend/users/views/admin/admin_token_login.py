# backend/users/views/admin/admin_token_login.py

from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from users.models import CustomUser

class AdminTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)

        if self.user.role != "admin":
            raise serializers.ValidationError("User is not authorized as Admin")

        # Add custom fields to token payload
        data['email'] = self.user.email
        data['role'] = self.user.role
        data['subscription_status'] = self.user.subscription_status
        return data


class AdminTokenObtainPairView(TokenObtainPairView):
    serializer_class = AdminTokenObtainPairSerializer
