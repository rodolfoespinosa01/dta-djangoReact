# --- Admin Password Reset Serializers ---
from rest_framework import serializers
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from users.models.custom_user import CustomUser
from users.models.admin.admin_password_reset_token import AdminPasswordResetToken
from django.contrib.auth.hashers import make_password

# 🔐 Step 1: Request password reset by email
class AdminForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    # ✅ Make sure the email belongs to an active admin
    def validate_email(self, value):
        if not CustomUser.objects.filter(email=value, role='admin', is_active=True).exists():
            raise serializers.ValidationError("No active admin account found with this email.")
        return value

    def save(self):
        email = self.validated_data['email']
        user = CustomUser.objects.get(email=email, role='admin', is_active=True)

        # 🔑 Generate token and UID for the reset URL
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        # 🗃️ Log token in DB for tracking / one-time use
        AdminPasswordResetToken.objects.create(user=user, token=token)

        # 📬 Simulated reset email (can later be replaced by real email service)
        reset_link = f"http://localhost:3000/admin_reset_password?uid={uid}&token={token}"

        print("\n=================== 📩 Admin Password Reset Email ===================")
        print(f"To: {email}")
        print("Subject: Reset Your Admin Password")
        print("Body:")
        print(f"Hi {user.username}, click the link below to reset your password:")
        print(f"➡️  {reset_link}")
        print("===================================================================\n")

# 🔒 Step 2: Confirm password reset (with UID + token + new password)
class AdminResetPasswordSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)

    def validate(self, data):
        # Decode UID and retrieve the user
        try:
            uid = force_str(urlsafe_base64_decode(data['uid']))
            user = CustomUser.objects.get(pk=uid, role='admin', is_active=True)
        except Exception:
            raise serializers.ValidationError("Invalid or expired UID.")

        # Verify the token with Django's token generator
        if not default_token_generator.check_token(user, data['token']):
            raise serializers.ValidationError("Invalid or expired token.")

        # Check if token is still in DB (ensures one-time use)
        if not AdminPasswordResetToken.objects.filter(user=user, token=data['token']).exists():
            raise serializers.ValidationError("Token not found or already used.")

        self.user = user
        return data

    def save(self):
        # Securely
