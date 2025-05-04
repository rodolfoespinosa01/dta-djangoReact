import stripe
from django.conf import settings
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

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
        # Free trial user logic
        if profile.trial_start_date and not profile.is_trial_expired():
            # Free trial still active — deactivate immediately
            profile.is_canceled = True
            profile.subscription_active = False
            profile.canceled_at = now
            profile.subscription_end_date = now
            profile.next_billing_date = None
            profile.auto_renew_cancelled = True
            profile.save()

            return Response({
                'success': True,
                'message': 'Your free trial has been canceled and your account is now inactive.'
            }, status=status.HTTP_200_OK)

        else:
            # Paid subscription — cancel at period end
            stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True
            )

            # Fetch updated subscription info
            subscription = stripe.Subscription.retrieve(subscription_id)
            current_period_end = subscription.get('current_period_end')

            if current_period_end:
                subscription_end = timezone.datetime.fromtimestamp(current_period_end, tz=timezone.utc)
            else:
                subscription_end = profile.next_billing_date or (now + timezone.timedelta(days=30))  # fallback

            profile.is_canceled = True
            profile.canceled_at = now
            profile.auto_renew_cancelled = True
            profile.subscription_end_date = subscription_end
            profile.next_billing_date = None
            profile.save()

            return Response({
                'success': True,
                'message': 'Your subscription will cancel at the end of your billing period.',
                'subscription_ends': subscription_end
            }, status=status.HTTP_200_OK)

    except stripe.error.StripeError as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
