from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
import stripe
from django.conf import settings

from users.admin_area.models import Profile, AccountHistory, Plan
from users.admin_area.utils.account_logger import log_account_event

stripe.api_key = settings.STRIPE_SECRET_KEY

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_subscription(request):
    user = request.user

    if user.role != 'admin':
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

    try:
        profile = user.profiles.get(is_current=True)
    except Profile.DoesNotExist:
        return Response({'error': 'Profile not found'}, status=status.HTTP_404_NOT_FOUND)

    plan_name = user.subscription_status
    is_trial = plan_name == 'admin_trial'
    now = timezone.now()

    # Mark canceled in Profile
    profile.is_canceled = True
    profile.canceled_at = now

    if is_trial:
        # Trial accounts: keep subscription_end_date = trial_end
        profile.save()

        log_account_event(
            event_type='cancel_subscription',
            email=user.email,
            plan_name=plan_name,
            stripe_customer_id=profile.stripe_customer_id,
            stripe_subscription_id=profile.stripe_subscription_id,
            cancelled_at=now,
        )

        return Response({
            'message': 'Free trial canceled. You will retain access for the full 14-day trial.'
        })

    # Paid subscriptions: cancel via Stripe and mark end date
    try:
        stripe.Subscription.modify(
            profile.stripe_subscription_id,
            cancel_at_period_end=True
        )
    except stripe.error.StripeError as e:
        return Response({'error': f'Stripe error: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

    # Update Profile end date
    profile.subscription_end_date = profile.next_billing_date
    profile.next_billing_date = None
    profile.save()

    log_account_event(
        event_type='cancel_subscription',
        email=user.email,
        plan_name=plan_name,
        stripe_customer_id=profile.stripe_customer_id,
        stripe_subscription_id=profile.stripe_subscription_id,
        cancelled_at=now,
    )

    return Response({
        'message': f'{plan_name} subscription canceled. You will retain access until {profile.subscription_end_date.date()}'
    })
