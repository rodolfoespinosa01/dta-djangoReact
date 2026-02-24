from rest_framework import serializers  # 👉 base class for creating custom api serializers
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator  # 👉 generates secure password reset tokens
from django.utils.http import urlsafe_base64_encode  # 👉 encodes the user id into a url-safe format
from django.utils.encoding import force_bytes  # 👉 converts user id into bytes for encoding
from core.models import CustomUser  # 👉 imports the custom user model
from users.admin_area.models import PasswordResetToken  # 👉 model that stores password reset tokens


class ForgotPasswordSerializer(serializers.Serializer):  # 👉 handles the password reset request (step 1 of the flow)
    email = serializers.EmailField()  # 👉 input field for the admin's email address

    def validate_email(self, value):
        if not CustomUser.objects.filter(email=value, role='admin', is_active=True).exists():
            raise serializers.ValidationError("No active admin account found with this email.")
        return value  # 👉 ensures that the email belongs to an active admin user

    def save(self):
        email = self.validated_data['email']
        user = CustomUser.objects.get(email=email, role='admin', is_active=True)

        token = default_token_generator.make_token(user)  # 👉 generates a secure password reset token
        uid = urlsafe_base64_encode(force_bytes(user.pk))  # 👉 encodes the user id into a url-safe string

        PasswordResetToken.objects.create(user=user, token=token)  # 👉 saves the token to the database for validation

        frontend_url = getattr(settings, "FRONTEND_URL", None) or "https://localhost:3000"
        reset_link = f"{frontend_url}/admin_reset_password?uid={uid}&token={token}"  # 👉 builds the reset link for the frontend

        print("\n=================== 📩 Admin Password Reset Email ===================")
        print(f"To: {email}")
        print("Subject: Reset Your Admin Password")
        print("Body:")
        print(f"Hi {user.username}, click the link below to reset your password:")
        print(f"➡️  {reset_link}")
        print("===================================================================\n")  # 👉 simulates sending a reset email (for dev)



# 👉 summary:
# validates admin emails for password reset and generates a secure token + uid.
# stores the token in the database and prints a reset link to the console for testing.
# part of the admin forgot password flow to handle secure password recovery.
