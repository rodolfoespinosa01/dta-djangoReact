import stripe
from django.http import HttpResponse
from django.utils.crypto import get_random_string
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from users.admin_area.models import (
    Plan, PendingSignup, PreCheckoutEmail,
    Profile, AccountHistory
)

stripe.api_key = settings.STRIPE_SECRET_KEY
endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
User = get_user_model()


@api_view(['POST'])
@permission_classes([AllowAny])
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        print("❌ signature verification failed")
        return HttpResponse(status=400)

    # ============ CHECKOUT SESSION (PAID) ============
    if event['type'] == 'checkout.session.completed':
        session_data = event['data']['object']
        session_id = session_data.get("id")
        session = stripe.checkout.Session.retrieve(session_id)
        print(f"🔎 Retrieved session metadata: {session.get('metadata')}")

        if session.get("payment_status") != "paid":
            print("⚠️ session completed without payment. skipping.")
            return HttpResponse(status=200)

        customer_email = session.get('customer_email') or stripe.Customer.retrieve(session.get('customer')).get('email')
        subscription_id = session.get('subscription')

        print(f"📡 stripe webhook triggered for: {customer_email} | session_id: {session_id}")
        
        plan_name = session.get('metadata', {}).get('plan_name')
        if not plan_name:
            print("❌ missing plan_name in metadata")
            return HttpResponse(status=500)

        try:
            plan = Plan.objects.get(name=plan_name)
        except Plan.DoesNotExist:
            print(f"❌ plan not found: {plan_name}")
            return HttpResponse(status=500)

        # 🧹 clean pre-checkout email logs
        PreCheckoutEmail.objects.filter(email=customer_email).delete()

        # 🛑 check for duplicate signup
        if PendingSignup.objects.filter(session_id=session_id).exists():
            print(f"⚠️ duplicate PendingSignup detected for session: {session_id}")
            return HttpResponse(status=200)

        # ✅ Create PendingSignup
        token = get_random_string(64)
        PendingSignup.objects.create(
            email=customer_email,
            session_id=session_id,
            token=token,
            plan=plan_name,
            subscription_id=subscription_id,
            stripe_customer_id=session.get('customer'),
            stripe_transaction_id=session.get('payment_intent')
        )

        registration_link = f"http://localhost:3000/admin_register?token={token}"
        print("\n" + "=" * 60)
        print("📩 registration email:")
        print(f"to: {customer_email}")
        print(f"➡️ {registration_link}")
        print("=" * 60 + "\n")

    # ============ SUBSCRIPTION CREATED ============
    elif event['type'] == 'customer.subscription.created':
        subscription = event['data']['object']
        customer_id = subscription['customer']
        stripe_subscription_id = subscription['id']
        trial_end = subscription.get('trial_end')

        customer = stripe.Customer.retrieve(customer_id)
        email = customer.get('email')

        # If not using PendingSignup (already registered), log it
        if not PendingSignup.objects.filter(stripe_customer_id=customer_id).exists():
            print(f"📌 Subscription created: {email} | {stripe_subscription_id}")

            AccountHistory.objects.create(
                email=email,
                event_type='signup',
                plan_name='adminMonthly',
                stripe_customer_id=customer_id,
                stripe_subscription_id=stripe_subscription_id,
                subscription_start=timezone.now()
            )

    # ============ PAYMENT SUCCEEDED ============
    elif event['type'] == 'invoice.payment_succeeded':
        invoice = event['data']['object']
        subscription_id = invoice['subscription']
        customer_id = invoice['customer']
        payment_intent = invoice.get('payment_intent')
        amount_paid = invoice['amount_paid']

        customer = stripe.Customer.retrieve(customer_id)
        email = customer.get('email')

        print(f"💵 Payment succeeded: {email} | ${amount_paid / 100:.2f}")

        AccountHistory.objects.create(
            email=email,
            event_type='stripe_payment',
            plan_name='adminMonthly',
            stripe_customer_id=customer_id,
            stripe_subscription_id=subscription_id,
            stripe_transaction_id=payment_intent,
            payment_processed_on=timezone.now()
        )

    # ============ SUBSCRIPTION DELETED ============
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        customer_id = subscription['customer']
        stripe_subscription_id = subscription['id']

        customer = stripe.Customer.retrieve(customer_id)
        email = customer.get('email')

        print(f"🛑 Subscription canceled or expired: {email}")

        try:
            profile = Profile.objects.get(
                stripe_subscription_id=stripe_subscription_id,
                stripe_customer_id=customer_id,
                is_current=True
            )
            profile.is_active = False
            profile.is_current = False
            profile.subscription_end_date = timezone.now()
            profile.save()

            AccountHistory.objects.create(
                email=email,
                event_type='cancel',
                plan_name='adminMonthly',
                stripe_customer_id=customer_id,
                stripe_subscription_id=stripe_subscription_id,
                cancelled_at=timezone.now()
            )

        except Profile.DoesNotExist:
            print(f"⚠️ No active profile found for canceled sub: {stripe_subscription_id}")

    return HttpResponse(status=200)
