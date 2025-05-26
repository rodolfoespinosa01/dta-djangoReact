from rest_framework import serializers  # 👉 base class for creating custom api serializers
from django.utils.http import urlsafe_base64_decode  # 👉 decodes the uid from the reset link
from django.utils.encoding import force_str  # 👉 converts bytes to string
from django.contrib.auth.tokens import default_token_generator  # 👉 verifies token authenticity
from django.contrib.auth.hashers import make_password  # 👉 securely hashes the new password
from core.models import CustomUser  # 👉 imports the custom user model
from users.admin_area.models import PasswordResetToken  # 👉 model that stores password reset tokens


class ResetPasswordSerializer(serializers.Serializer):  # 👉 handles setting a new password using a uid + token
    uid = serializers.CharField()  # 👉 base64-encoded user id from the reset link
    token = serializers.CharField()  # 👉 secure token used to verify password reset intent
    new_password = serializers.CharField(write_only=True)  # 👉 the new password to set (write only for security)


    def validate(self, data):
        try:
            uid = force_str(urlsafe_base64_decode(data['uid']))  # 👉 decode uid from base64
            user = CustomUser.objects.get(pk=uid, role='admin', is_active=True)  # 👉 find active admin user
        except Exception:
            raise serializers.ValidationError("Invalid or expired UID.")

        if not default_token_generator.check_token(user, data['token']):  # 👉 check if the token is valid
            raise serializers.ValidationError("Invalid or expired token.")

        if not PasswordResetToken.objects.filter(user=user, token=data['token']).exists():  
            raise serializers.ValidationError("Token not found or already used.")  # 👉 prevents reuse of expired tokens

        self.user = user  # 👉 store validated user for use in save()
        return data


    def save(self):
        self.user.password = make_password(self.validated_data['new_password'])  # 👉 securely hashes the new password
        self.user.save()  # 👉 saves the updated user to the database
        PasswordResetToken.objects.filter(user=self.user).delete()  # 👉 removes the used token to prevent reuse


# 👉 summary:
# verifies the uid and token from the password reset link, sets a new password if valid,
# and deletes the reset token to prevent reuse. part of the admin password reset flow.