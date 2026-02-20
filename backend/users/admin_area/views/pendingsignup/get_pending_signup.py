from rest_framework.decorators import api_view
from rest_framework import status
from users.admin_area.models import PendingSignup
from users.admin_area.serializers.pending_signup import PendingSignupSerializer
from users.admin_area.views.api_contract import ok, error

@api_view(['GET'])
def get_pending_signup(request, token):
    try:
        pending = PendingSignup.objects.get(token=token)
        serializer = PendingSignupSerializer(pending)
        return ok(serializer.data, http_status=status.HTTP_200_OK)
    except PendingSignup.DoesNotExist:
        return error(code='INVALID_TOKEN', message='Invalid or expired token', http_status=status.HTTP_404_NOT_FOUND)
