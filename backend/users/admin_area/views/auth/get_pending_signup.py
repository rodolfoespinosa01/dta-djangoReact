from rest_framework.decorators import api_view, permission_classes  # 👉 enables function-based views and sets permissions
from rest_framework.permissions import AllowAny  # 👉 allows access to unauthenticated users
from rest_framework.response import Response  # 👉 used to return structured api responses
from rest_framework import status  # 👉 provides standard http status codes

from users.admin_area.models import PendingSignup  # 👉 imports the pending signup model used after stripe checkout


from users.admin_area.models import PendingSignup

@api_view(['GET'])  # 👉 allows only get requests to this view
@permission_classes([AllowAny])  # 👉 open to all users (no auth required)
def get_pending_signup(request, token):
    try:
        pending = PendingSignup.objects.get(token=token)  # 👉 tries to fetch the pending signup using the provided token
        return Response({'email': pending.email}, status=status.HTTP_200_OK)  # 👉 returns the associated email if found
    except PendingSignup.DoesNotExist:
        return Response({'error': 'Invalid or expired token'}, status=status.HTTP_404_NOT_FOUND)  # 👉 error if token is invalid


# 👉 summary:
# retrieves the email tied to a pending admin signup using a one-time token.
# used after stripe checkout to autofill or confirm the user's email before account creation.
# returns 404 if the token is invalid or expired.