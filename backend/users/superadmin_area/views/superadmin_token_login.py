from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers

class SuperAdminTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)

        if not self.user.is_superuser:
            raise serializers.ValidationError("Not authorized as SuperAdmin")

        data['username'] = self.user.username
        data['email'] = self.user.email
        data['role'] = 'superadmin'
        return data

class SuperAdminTokenObtainPairView(TokenObtainPairView):
    serializer_class = SuperAdminTokenObtainPairSerializer