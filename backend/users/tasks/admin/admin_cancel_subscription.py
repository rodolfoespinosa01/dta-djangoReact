import stripe
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

stripe.api_key = settings.STRIPE_SECRET_KEY

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_admin_subscription(request):
    user = request.user

    if user.role != 'admin':
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

    profile = user.admin_profile
    subscription_id = profile.admin_stripe_subscription_id

    if not subscription_id:
        return Response({'error': 'No active Stripe subscription found'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=True
        )
        profile.auto_renew_cancelled = True
        profile.save()

        return Response({
            'success': True,
            'message': 'Your subscription has been set to cancel. You’ll retain access until the current billing period ends.'
        }, status=status.HTTP_200_OK)

    except stripe.error.StripeError as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
