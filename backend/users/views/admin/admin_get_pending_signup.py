from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from adminplans.models import AdminPendingSignup

@api_view(['GET'])
@permission_classes([AllowAny])
def admin_get_pending_signup(request, token):
    try:
        pending = AdminPendingSignup.objects.get(token=token)
        return Response({'email': pending.email}, status=status.HTTP_200_OK)
    except AdminPendingSignup.DoesNotExist:
        return Response({'error': 'Invalid or expired token'}, status=status.HTTP_404_NOT_FOUND)
