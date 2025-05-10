from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from users.admin_area.serializers.forgot_password_serializer import ForgotPasswordSerializer

class AdminForgotPasswordView(APIView):
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "Password reset link sent (check terminal)."})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)