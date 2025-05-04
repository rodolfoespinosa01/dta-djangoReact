from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from users.admin_area.serializers import AdminResetPasswordSerializer



class AdminResetPasswordConfirmView(APIView):
    def post(self, request):
        serializer = AdminResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "Password has been reset successfully."})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
