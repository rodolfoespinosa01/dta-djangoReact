import stripe  # 👉 Stripe SDK for interacting with checkout sessions and subscriptions
from django.http import HttpResponse  # 👉 used to respond to Stripe webhook
from django.utils.crypto import get_random_string  # 👉 for generating unique tokens
from django.conf import settings  # 👉 used to load Stripe secret keys from environment
from rest_framework.decorators import api_view, permission_classes  # 👉 enables function-based views with permission control
from rest_framework.permissions import AllowAny  # 👉 required so Stripe can access the webhook endpoint

from users.admin_area.models import Plan, PendingSignup, PreCheckoutEmail  # 👉 core models used during admin registration
from users.admin_area.utils.account_logger import log_account_event  # 👉 (not used here but typically for logging)
from django.contrib.auth import get_user_model  # 👉 retrieves the active user model

stripe.api_key = settings.STRIPE_SECRET_KEY
endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
User = get_user_model()


@api_view(['POST'])
@permission_classes([AllowAny])  # 👉 this endpoint must be public so Stripe can hit it
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")  # 👉 used to verify authenticity of the event

    # 🛡️ Verify the webhook signature and parse the event
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        print("❌ Signature verification failed")
        return HttpResponse(status=400)


        # 🎯 We're only interested in completed checkout sessions
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']

        # 🔒 Skip if payment didn't succeed
        if session.get("payment_status") != "paid":
            print("⚠️ Session completed without payment. Skipping PendingSignup.")
            return HttpResponse(status=200)

        # 📥 Extract key session data
        session_id = session.get('id')
        customer_email = session.get('customer_email')
        subscription_id = session.get('subscription')

        # 🔄 If email is missing, try retrieving it from the customer object
        if not customer_email:
            customer_id = session.get('customer')
            if customer_id:
                customer = stripe.Customer.retrieve(customer_id)
                customer_email = customer.get('email')

        print(f"🔍 Webhook triggered for session: {session_id}")
        print(f"📧 Email: {customer_email}")
        print(f"🧾 Subscription ID: {subscription_id}")


        # 🛑 If the user already exists, this is a reactivation — no need to create a PendingSignup
        if User.objects.filter(email=customer_email).exists():
            print(f"✅ Reactivation detected for {customer_email}. No PendingSignup will be created.")
            return HttpResponse(status=200)

        # 🧠 Get plan_name from Stripe metadata
        raw_plan_name = session.get('metadata', {}).get('plan_name')
        if not raw_plan_name:
            print("❌ Missing plan_name in metadata")
            return HttpResponse(status=500)

        # 🎯 Normalize plan name if this was a free trial
        plan_name = 'adminMonthly' if raw_plan_name == 'adminTrial' else raw_plan_name

        try:
            plan = Plan.objects.get(name=plan_name)
        except Plan.DoesNotExist:
            print(f"❌ Plan not found for: {plan_name}")
            return HttpResponse(status=500)

        # 🔑 Create secure registration token for one-time use
        token = get_random_string(64)


        # 🧹 Clean up any pre-checkout email log to prevent clutter
        PreCheckoutEmail.objects.filter(email=customer_email).delete()

        # 🔁 Check if we already have a PendingSignup for this session
        existing = PendingSignup.objects.filter(session_id=session_id).first()
        if existing:
            print(f"⚠️ PendingSignup already exists for session: {session_id}, skipping duplicate.")

            # 📩 Reprint registration email if the token hasn’t been used yet
            if not existing.is_used:
                registration_link = f"http://localhost:3000/admin_register?token={existing.token}"
                print("\n" + "=" * 60)
                print("📩 Registration email (reprinted):")
                print(f"To: {existing.email}")
                print("Subject: Finish setting up your Admin Account")
                print(f"➡️ Click to register:\n{registration_link}")
                print("=" * 60 + "\n")

            return HttpResponse(status=200)

        # 📝 Create a new PendingSignup record tied to the Stripe session
        try:
            PendingSignup.objects.create(
                email=customer_email,
                session_id=session_id,
                token=token,
                plan=raw_plan_name,
                subscription_id=subscription_id,
                stripe_customer_id=session.get('customer'),
                stripe_transaction_id=session.get('payment_intent')
            )

            # 📩 Simulated email: print registration link to console
            registration_link = f"http://localhost:3000/admin_register?token={token}"
            print("\n" + "=" * 60)
            print("📩 Registration email:")
            print(f"To: {customer_email}")
            print("Subject: Finish setting up your Admin Account")
            print(f"➡️ Click to register:\n{registration_link}")
            print("=" * 60 + "\n")

        except Exception as e:
            print(f"❌ Error saving PendingSignup: {str(e)}")
            return HttpResponse(status=500)


    # ✅ Always return 200 so Stripe doesn't retry the event
    return HttpResponse(status=200)



# 👉 summary:
# handles the `checkout.session.completed` event from Stripe.
# verifies the webhook signature, extracts customer and plan info,
# and creates a PendingSignup if the admin is a new user.
# skips signup creation for existing users (reactivations).
# generates a unique token for registration and prints a simulated email link to the console.
# ensures a consistent, secure admin onboarding flow after Stripe checkout.