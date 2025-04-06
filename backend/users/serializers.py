# --- Token serializer for login ---
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token['email'] = user.email
        token['role'] = user.role
        token['is_superuser'] = user.is_superuser

        return token

# --- Admin Password Reset Serializers ---
from rest_framework import serializers
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from .models import CustomUser, AdminPasswordResetToken
from django.contrib.auth.hashers import make_password

class AdminForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not CustomUser.objects.filter(email=value, role='admin', is_active=True).exists():
            raise serializers.ValidationError("No active admin account found with this email.")
        return value

    def save(self):
        email = self.validated_data['email']
        user = CustomUser.objects.get(email=email, role='admin', is_active=True)
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        AdminPasswordResetToken.objects.create(user=user, token=token)

        reset_link = f"http://localhost:3000/adminresetpassword?uid={uid}&token={token}"

        print("\n=================== 📩 Admin Password Reset Email ===================")
        print(f"To: {email}")
        print("Subject: Reset Your Admin Password")
        print("Body:")
        print(f"Hi {user.username}, click the link below to reset your password:")
        print(f"➡️  {reset_link}")
        print("===================================================================\n")

class AdminResetPasswordSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)

    def validate(self, data):
        try:
            uid = force_str(urlsafe_base64_decode(data['uid']))
            user = CustomUser.objects.get(pk=uid, role='admin', is_active=True)
        except Exception:
            raise serializers.ValidationError("Invalid or expired UID.")

        if not default_token_generator.check_token(user, data['token']):
            raise serializers.ValidationError("Invalid or expired token.")

        # Optional: Check DB token existence and expiry
        if not AdminPasswordResetToken.objects.filter(user=user, token=data['token']).exists():
            raise serializers.ValidationError("Token not found or already used.")

        self.user = user
        return data

    def save(self):
        self.user.password = make_password(self.validated_data['new_password'])
        self.user.save()
        AdminPasswordResetToken.objects.filter(user=self.user).delete()