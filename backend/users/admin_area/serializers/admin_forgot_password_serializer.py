from rest_framework import serializers
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from core.models import CustomUser
from users.admin_area.models import AdminPasswordResetToken

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

        reset_link = f"http://localhost:3000/admin_reset_password?uid={uid}&token={token}"

        print("\n=================== 📩 Admin Password Reset Email ===================")
        print(f"To: {email}")
        print("Subject: Reset Your Admin Password")
        print("Body:")
        print(f"Hi {user.username}, click the link below to reset your password:")
        print(f"➡️  {reset_link}")
        print("===================================================================\n")
