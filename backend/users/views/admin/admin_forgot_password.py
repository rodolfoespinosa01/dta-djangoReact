from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from users.serializers.admin_serializers import AdminForgotPasswordSerializer

class AdminForgotPasswordView(APIView):
    # POST endpoint to trigger password reset
    def post(self, request):
        # Deserialize and validate the input (typically just an email)
        serializer = AdminForgotPasswordSerializer(data=request.data)
        
        if serializer.is_valid():
            # Trigger the serializer's save logic (e.g., create token + send email)
            serializer.save()
            return Response({"detail": "Password reset link sent (check terminal)."})
        
        # Return validation errors (e.g., invalid email format or missing field)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
