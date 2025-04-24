from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from adminplans.models import AdminPendingSignup

@api_view(['GET'])  # ✅ Only accepts GET requests
@permission_classes([AllowAny])  # 🔓 Public endpoint (used before user is created)
def admin_get_pending_signup(request, token):
    try:
        # 🔍 Look up pending signup using the token (from email link)
        pending = AdminPendingSignup.objects.get(token=token)

        # ✅ Token is valid — return associated email
        return Response({'email': pending.email}, status=status.HTTP_200_OK)

    except AdminPendingSignup.DoesNotExist:
        # ❌ Invalid or expired token
        return Response({'error': 'Invalid or expired token'}, status=status.HTTP_404_NOT_FOUND)
