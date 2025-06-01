from rest_framework.decorators import api_view, permission_classes  # 👉 enables function-based api views and permission control
from rest_framework.permissions import IsAuthenticated  # 👉 requires user to be logged in
from rest_framework.response import Response  # 👉 returns structured responses
from rest_framework import status  # 👉 standard http status codes
from django.utils import timezone  # 👉 used to track cancel timestamps
import stripe  # 👉 stripe api for subscription management
from django.conf import settings  # 👉 access to stripe secret key from environment

from users.admin_area.models import Profile, AccountHistory, Plan  # 👉 key models for subscription tracking
from users.admin_area.utils.history_creator import log_history_event  # 👉 logs cancel event to AccountHistory

stripe.api_key = settings.STRIPE_SECRET_KEY  # 👉 set the stripe api key for requests


@api_view(['POST'])  # 👉 allows only POST requests
@permission_classes([IsAuthenticated])  # 👉 requires auth (admin must be logged in)
def cancel_subscription(request):
    user = request.user

    if user.role != 'admin':
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
    # 👉 only admin users can cancel subscriptions

    try:
        profile = user.profiles.get(is_current=True)
    except Profile.DoesNotExist:
        return Response({'error': 'Profile not found'}, status=status.HTTP_404_NOT_FOUND)
    # 👉 ensures the current billing profile exists

    plan_name = user.subscription_status
    is_trial = plan_name == 'admin_trial'
    now = timezone.now()

        # 👉 mark profile as canceled
    profile.is_canceled = True
    profile.canceled_at = now

    if is_trial:
        # 👉 trial: allow access until trial ends without stripe cancellation
        profile.save()

        log_history_event(
            event_type='cancel_subscription',
            email=user.email,
            plan_name=plan_name,
            cancelled_at=now,
        )

        return Response({
            'message': 'Free trial canceled. You will retain access for the full 14-day trial.'
        })

        # 👉 paid plan: cancel stripe subscription and update profile
    try:
        stripe.Subscription.modify(
            profile.stripe_subscription_id,
            cancel_at_period_end=True
        )
    except stripe.error.StripeError as e:
        return Response({'error': f'Stripe error: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

    # 👉 update profile with end date and clear next billing
    profile.subscription_end_date = profile.next_billing_date
    profile.next_billing_date = None
    profile.save()

    log_history_event(
        event_type='cancel_subscription',
        email=user.email,
        plan_name=plan_name,
        cancelled_at=now,
    )

    return Response({
        'message': f'{plan_name} subscription canceled. You will retain access until {profile.subscription_end_date.date()}'
    })


# 👉 summary:
# cancels the current admin subscription (trial or paid).
# if trial: simply flags the profile as canceled and logs the event.
# if paid: updates stripe to cancel at end of period, updates profile with end date,
# logs the cancel event, and confirms cancellation to the user.