from rest_framework.views import APIView  # 👉 base class for building API views
from rest_framework.response import Response  # 👉 used to return JSON responses
from rest_framework import status  # 👉 standard HTTP status codes
from users.admin_area.serializers import ResetPasswordSerializer  # 👉 handles validation and logic for setting new password


class ResetPasswordConfirmView(APIView):
    # 👉 accepts uid, token, and new password to finalize the reset process

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)  # 📨 expects uid, token, and new_password

        if serializer.is_valid():
            serializer.save()  # 🔐 updates user password and deletes used reset token
            return Response({"detail": "Password has been reset successfully."})  # ✅ confirmation response

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)  # ❌ error if token is invalid or expired


# 👉 summary:
# confirms a password reset using the token and uid sent in the reset email.
# verifies the token, validates the new password, updates the user record,
# and deletes the used PasswordResetToken.
# used as the final step in the "Forgot Password" flow.