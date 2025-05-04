from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from users.admin_area.serializers import AdminForgotPasswordSerializer

class AdminForgotPasswordView(APIView):
    def post(self, request):
        serializer = AdminForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "Password reset link sent (check terminal)."})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
