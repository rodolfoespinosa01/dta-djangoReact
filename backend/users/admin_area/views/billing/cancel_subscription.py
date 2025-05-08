import stripe
from django.conf import settings
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from users.admin_area.utils.account_logger import log_account_event

stripe.api_key = settings.STRIPE_SECRET_KEY

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_subscription(request):
    user = request.user

    if user.role != 'admin':
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

    profile = user.profile
    subscription_id = profile.stripe_subscription_id
    customer_id = profile.stripe_customer_id
    plan_name = user.subscription_status
    now = timezone.now()

    if not subscription_id:
        return Response({'error': 'No active Stripe subscription found'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Free trial user logic
        if profile.trial_start_date and not profile.is_trial_expired():
            profile.is_canceled = True
            profile.subscription_active = False
            profile.canceled_at = now
            profile.subscription_end_date = now
            profile.next_billing_date = None
            profile.auto_renew_cancelled = True
            profile.save()

            log_account_event(
                user=user,
                event_type='cancel',
                plan_name=plan_name,
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
                cancelled_at=now
            )

            return Response({
                'success': True,
                'message': 'Your free trial has been canceled and your account is now inactive.'
            }, status=status.HTTP_200_OK)

        else:
            stripe.Subscription.modify(subscription_id, cancel_at_period_end=True)
            subscription = stripe.Subscription.retrieve(subscription_id)
            current_period_end = subscription.get('current_period_end')

            if current_period_end:
                subscription_end = timezone.datetime.fromtimestamp(current_period_end, tz=timezone.utc)
            else:
                subscription_end = profile.next_billing_date or (now + timezone.timedelta(days=30))

            profile.is_canceled = True
            profile.canceled_at = now
            profile.auto_renew_cancelled = True
            profile.subscription_end_date = subscription_end
            profile.next_billing_date = None
            profile.save()

            log_account_event(
                user=user,
                event_type='cancel',
                plan_name=plan_name,
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
                cancelled_at=now
            )

            return Response({
                'success': True,
                'message': 'Your subscription will cancel at the end of your billing period.',
                'subscription_ends': subscription_end
            }, status=status.HTTP_200_OK)

    except stripe.error.StripeError as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
