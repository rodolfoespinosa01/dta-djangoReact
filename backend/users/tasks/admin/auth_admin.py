import json
import stripe
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from adminplans.models import PendingAdminSignup

def get_pending_admin_signup(request, token):
    try:
        pending = PendingAdminSignup.objects.get(token=token)
        return JsonResponse({'email': pending.email})
    except PendingAdminSignup.DoesNotExist:
        return JsonResponse({'error': 'Invalid or expired token'}, status=404)

@csrf_exempt
def login_admin(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST request required'}, status=400)
    
    try:
        data = json.loads(request.body)
        email = data.get('email')
        password = data.get('password')

        user = authenticate(request, username=email, password=password)

        if user is None:
            return JsonResponse({'error': 'Invalid credentials'}, status=401)

        if user.role != 'admin':
            return JsonResponse({'error': 'Not an Admin account'}, status=403)

        login(request, user)

        return JsonResponse({'success': True, 'message': 'Logged in as admin'})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_admin_trial_auto_renew(request):
    user = request.user
    if user.role != 'admin' or user.subscription_status != 'admin_trial':
        return Response({'error': 'Unauthorized or not a trial admin'}, status=403)

    profile = user.admin_profile
    subscription_id = profile.admin_stripe_subscription_id

    if not subscription_id:
        return Response({'error': 'No Stripe subscription found'}, status=400)

    try:
        # ❗ This is what actually stops Stripe from charging the user
        stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=True
        )
        profile.auto_renew_cancelled = True
        profile.save()

        return Response({'success': True, 'message': 'Trial cancellation confirmed. You will not be charged after your 14-day trial ends.'})
    except stripe.error.StripeError as e:
        return Response({'error': str(e)}, status=500)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_admin_subscription(request):
    user = request.user

    # Ensure user is an admin and on a paid plan
    if user.role != 'admin' or user.subscription_status not in ['admin_monthly', 'admin_quarterly', 'admin_annual']:
        return Response({'error': 'Unauthorized or not on a paid admin plan'}, status=403)

    profile = user.admin_profile
    subscription_id = profile.admin_stripe_subscription_id

    if not subscription_id:
        return Response({'error': 'No active Stripe subscription found'}, status=400)

    try:
        # Cancel at period end (retains access until current cycle ends)
        stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=True
        )

        # Update flag in profile
        profile.auto_renew_cancelled = True
        profile.save()

        return Response({
            'success': True,
            'message': 'Subscription cancellation scheduled. You will retain access until the end of the current billing cycle.'
        })

    except stripe.error.StripeError as e:
        return Response({'error': str(e)}, status=500)
