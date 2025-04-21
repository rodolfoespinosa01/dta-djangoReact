import stripe
from django.conf import settings
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from adminplans.models import AdminAccountHistory
from datetime import timezone as dt_timezone



stripe.api_key = settings.STRIPE_SECRET_KEY

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_cancel_subscription(request):
    user = request.user

    if user.role != 'admin':
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

    profile = user.admin_profile
    subscription_id = profile.admin_stripe_subscription_id
    now = timezone.now()

    if not subscription_id:
        return Response({'error': 'No active Stripe subscription found'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Cancel Stripe subscription at period end
        stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=True
        )

        # Retrieve full subscription to get current_period_end
        subscription = stripe.Subscription.retrieve(subscription_id)
        current_period_end = subscription.get('current_period_end')

        if current_period_end:
            subscription_end = timezone.datetime.fromtimestamp(current_period_end, tz=dt_timezone.utc)
        else:
            # Fallback if period end not available (e.g., trial or setup error)
            subscription_end = profile.next_billing_date or (now + timezone.timedelta(days=14))

        # Update profile
        profile.is_canceled = True
        profile.canceled_at = now
        profile.auto_renew_cancelled = True
        profile.subscription_end_date = subscription_end
        profile.next_billing_date = None  # 🔥 Clear this to avoid confusion
        profile.save()

        AdminAccountHistory.objects.create(
            admin=user,
            plan_name=user.subscription_status,
            subscription_id=profile.admin_stripe_subscription_id,
            start_date=profile.subscription_started_at or now,
            end_date=subscription_end,
            was_canceled=True
        )


        return Response({
            'success': True,
            'message': 'Your subscription will cancel at the end of your billing period.',
            'subscription_ends': subscription_end
        }, status=status.HTTP_200_OK)

    except stripe.error.StripeError as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
