import stripe
from django.http import HttpResponse
from django.utils.crypto import get_random_string
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.contrib.auth import get_user_model

from users.admin_area.models import Plan, PendingSignup, PreCheckoutEmail
from users.admin_area.utils.reactivate_profile import handle_admin_reactivation  # 🔁 helper module

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

    if event['type'] == 'checkout.session.completed':
        session_data = event['data']['object']
        session_id = session_data.get("id")
        session = stripe.checkout.Session.retrieve(session_id)
        print(f"🔎 Retrieved session metadata: {session.get('metadata')}")



        if session.get("payment_status") != "paid":
            print("⚠️ session completed without payment. skipping.")
            return HttpResponse(status=200)

        session_id = session.get('id')
        customer_email = session.get('customer_email') or stripe.Customer.retrieve(session.get('customer')).get('email')
        subscription_id = session.get('subscription')

        print(f"📡 stripe webhook triggered for: {customer_email} | session_id: {session_id}")

        # ✅ handle reactivation flow for existing users
        if User.objects.filter(email=customer_email).exists():
            print(f"🔁 existing user detected — invoking reactivation handler for {customer_email}")
            try:
                handle_admin_reactivation(session)
            except Exception as e:
                print(f"❌ reactivation failed: {str(e)}")
                return HttpResponse(status=500)
            return HttpResponse(status=200)

        # 🆕 handle first-time admin signup
        plan_name = session.get('metadata', {}).get('plan_name')
        if not plan_name:
            print("❌ missing plan_name in metadata")
            return HttpResponse(status=500)

        # normalize adminTrial to adminMonthly internally
        plan_name = session.get('metadata', {}).get('plan_name')

        try:
            plan = Plan.objects.get(name=plan_name)
        except Plan.DoesNotExist:
            print(f"❌ plan not found: {plan_name}")
            return HttpResponse(status=500)

        # 🧹 clean pre-checkout email logs
        PreCheckoutEmail.objects.filter(email=customer_email).delete()

        # check for duplicate pending signup
        if PendingSignup.objects.filter(session_id=session_id).exists():
            print(f"⚠️ duplicate PendingSignup detected for session: {session_id}")
            return HttpResponse(status=200)

        # 🆕 create PendingSignup and print simulated registration email
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

    return HttpResponse(status=200)