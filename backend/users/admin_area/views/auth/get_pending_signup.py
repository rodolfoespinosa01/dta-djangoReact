from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from users.admin_area.models import PendingSignup

@api_view(['GET']) 
@permission_classes([AllowAny])  
def get_pending_signup(request, token):
    try:
        pending = PendingSignup.objects.get(token=token)
        return Response({'email': pending.email}, status=status.HTTP_200_OK)
    except PendingSignup.DoesNotExist:
        return Response({'error': 'Invalid or expired token'}, status=status.HTTP_404_NOT_FOUND)
