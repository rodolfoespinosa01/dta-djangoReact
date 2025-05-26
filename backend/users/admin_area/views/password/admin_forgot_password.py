from rest_framework.views import APIView  # 👉 base class for building a custom API endpoint
from rest_framework.response import Response  # 👉 used to return JSON responses
from rest_framework import status  # 👉 standard HTTP status codes
from users.admin_area.serializers.forgot_password_serializer import ForgotPasswordSerializer  # 👉 handles validation and reset logic


class AdminForgotPasswordView(APIView):
    # 👉 handles POST requests to initiate admin password reset

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)  # 📨 takes in an email input

        if serializer.is_valid():
            serializer.save()  # 📩 generates token, creates record, prints reset link to terminal
            return Response({"detail": "Password reset link sent (check terminal)."})  # ✅ success message

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)  # ❌ if validation fails (e.g., no matching admin)


# 👉 summary:
# accepts admin email and triggers the password reset flow.
# validates the email using ForgotPasswordSerializer,
# creates a PasswordResetToken and prints a reset link to the terminal.
# used in the "Forgot Password?" form on the admin login screen.