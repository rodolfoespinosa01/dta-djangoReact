from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from users.admin_area.models import PendingSignup
from users.admin_area.serializers.pending_signup import PendingSignupSerializer

@api_view(['GET'])
def get_pending_signup(request, token):
    try:
        pending = PendingSignup.objects.get(token=token)
        serializer = PendingSignupSerializer(pending)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except PendingSignup.DoesNotExist:
        return Response({'error': 'Invalid or expired token'}, status=status.HTTP_404_NOT_FOUND)