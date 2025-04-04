from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import stripe
from django.utils.timezone import datetime
from .models import Subscription
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def attach_subscription_to_user(request):
    session_id = request.data.get("session_id")
    if not session_id:
        return Response({"error": "Session ID required."}, status=400)

    try:
        session = stripe.checkout.Session.retrieve(session_id)
        subscription = stripe.Subscription.retrieve(session.subscription)

        Subscription.objects.update_or_create(
            user=request.user,
            defaults={
                "stripe_subscription_id": subscription.id,
                "plan_type": subscription['items']['data'][0]['price']['recurring']['interval'],
                "status": subscription.status,
                "current_period_end": datetime.fromtimestamp(subscription.current_period_end),
                "trial_used": subscription.trial_end is not None
            }
        )

        return Response({"message": "Subscription attached successfully."})
    
    except Exception as e:
        return Response({"error": str(e)}, status=400)
