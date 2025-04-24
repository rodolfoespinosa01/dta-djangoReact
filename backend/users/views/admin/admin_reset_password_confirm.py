from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from users.serializers.admin_serializers import AdminResetPasswordSerializer


class AdminResetPasswordConfirmView(APIView):
    # POST endpoint to confirm password reset using token + new password
    def post(self, request):
        # Deserialize and validate input (token + new_password)
        serializer = AdminResetPasswordSerializer(data=request.data)

        if serializer.is_valid():
            # ✅ Save new password via serializer logic (usually updates the user object)
            serializer.save()
            return Response({"detail": "Password has been reset successfully."})

        # ❌ Validation failed (invalid token, weak password, etc.)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
