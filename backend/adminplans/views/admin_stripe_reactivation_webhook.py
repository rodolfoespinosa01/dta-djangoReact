import stripe
import time
from datetime import timezone as dt_timezone
from django.http import HttpResponse
from django.utils import timezone
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from users.models import CustomUser
from adminplans.models import AdminProfile, AdminPlan, AdminAccountHistory

stripe.api_key = settings.STRIPE_SECRET_KEY
endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

@api_view(['POST'])
@permission_classes([AllowAny])
def admin_stripe_reactivation_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        print("❌ Stripe signature verification failed")
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        metadata = session.get('metadata', {})

        # ✅ Skip if not a reactivation session
        if 'reactivated_email' not in metadata:
            print("ℹ️ Not a reactivation session — skipping.")
            return HttpResponse(status=200)

        email = metadata.get('reactivated_email')
        plan_name = metadata.get('plan_name')
        subscription_id = session.get('subscription')

        print(f"📦 Reactivation Webhook: email={email}, plan={plan_name}, subscription_id={subscription_id}")

        if not email or not subscription_id or not plan_name:
            print("❌ Missing metadata in session")
            return HttpResponse(status=400)

        try:
            user = CustomUser.objects.get(email=email, role='admin')
            profile = user.admin_profile
            plan = AdminPlan.objects.get(name=plan_name)

            # ✅ Retrieve full subscription details from Stripe
            stripe_subscription = stripe.Subscription.retrieve(subscription_id)
            subscription_items = stripe_subscription.get('items', {}).get('data', [])
            current_period_end = subscription_items[0].get('current_period_end') if subscription_items else None

            if not current_period_end:
                print("⚠️ current_period_end missing — retrying in 2s")
                time.sleep(2)
                stripe_subscription = stripe.Subscription.retrieve(subscription_id)
                print("🔍 Subscription retry payload:", stripe_subscription)
                subscription_items = stripe_subscription.get('items', {}).get('data', [])
                current_period_end = subscription_items[0].get('current_period_end') if subscription_items else None

            if not current_period_end:
                print("❌ Stripe subscription is STILL missing current_period_end")
                return HttpResponse(status=500)

            period_end_date = timezone.datetime.fromtimestamp(current_period_end, tz=dt_timezone.utc)
            now = timezone.now()

            print("🔄 Updating AdminProfile...")

            # ✅ Update AdminProfile
            profile.admin_stripe_subscription_id = subscription_id
            profile.subscription_started_at = now
            profile.next_billing_date = period_end_date
            profile.subscription_end_date = None
            profile.is_canceled = False
            profile.canceled_at = None
            profile.auto_renew_cancelled = False
            profile.save()

            print("📘 AdminProfile updated")

            # ✅ Log into AdminAccountHistory
            AdminAccountHistory.objects.create(
                admin=user,
                plan_name=plan_name,
                subscription_id=subscription_id,
                start_date=now,
                end_date=None,
                was_canceled=False
            )

            print(f"✅ Reactivation successful for {email}")

        except Exception as e:
            print(f"❌ Reactivation webhook error: {str(e)}")
            return HttpResponse(status=500)

    return HttpResponse(status=200)