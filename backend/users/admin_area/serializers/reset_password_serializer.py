from rest_framework import serializers
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.hashers import make_password
from core.models import CustomUser
from users.admin_area.models import PasswordResetToken

class ResetPasswordSerializer(serializers.Serializer):
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

        if not PasswordResetToken.objects.filter(user=user, token=data['token']).exists():
            raise serializers.ValidationError("Token not found or already used.")

        self.user = user
        return data

    def save(self):
        self.user.password = make_password(self.validated_data['new_password'])
        self.user.save()
        PasswordResetToken.objects.filter(user=self.user).delete()
