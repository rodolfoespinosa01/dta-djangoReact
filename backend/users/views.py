from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from users.admin_area.views.billing.stripe_webhook import stripe_webhook as admin_stripe_webhook
from users.client_area.views.billing import client_stripe_webhook


@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def unified_stripe_webhook(request):
    """
    Local/dev convenience endpoint:
    dispatch a single Stripe event stream to both admin and client handlers.
    """
    # DRF wraps the Django HttpRequest; downstream handlers expect raw HttpRequest.
    raw_request = getattr(request, "_request", request)

    admin_response = admin_stripe_webhook(raw_request)
    client_response = client_stripe_webhook(raw_request)

    admin_status = getattr(admin_response, "status_code", 200)
    client_status = getattr(client_response, "status_code", 200)
    if admin_status >= 400 and client_status >= 400:
        return HttpResponse(status=400)
    return HttpResponse(status=200)
