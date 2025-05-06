from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from users.admin_area.serializers.forgot_password_serializer import ForgotPasswordSerializer

class ForgotPasswordView(APIView):
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "Password reset email sent."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
