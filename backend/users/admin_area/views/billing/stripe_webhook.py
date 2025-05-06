import stripe
from django.http import HttpResponse
from django.utils.crypto import get_random_string
from django.utils import timezone
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from users.admin_area.models import Plan, PendingSignup

stripe.api_key = settings.STRIPE_SECRET_KEY
endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

@api_view(['POST'])
@permission_classes([AllowAny])
def stripe_webhook(request):
    token = get_random_string(length=64)
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        print("❌ Signature verification failed")
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        session_id = session.get('id')
        customer_email = session.get('customer_email')
        subscription_id = session.get('subscription')

        # Fallback if email missing
        if not customer_email:
            customer_id = session.get('customer')
            if customer_id:
                customer = stripe.Customer.retrieve(customer_id)
                customer_email = customer.get('email')

        print(f"🔍 Webhook triggered for session: {session_id}")
        print(f"📧 Email: {customer_email}")
        print(f"🧾 Subscription ID: {subscription_id}")

        # Metadata from checkout creation
        raw_plan_name = session.get('metadata', {}).get('plan_name')
        if not raw_plan_name:
            print("❌ Missing plan_name in metadata")
            return HttpResponse(status=500)

        # Normalize: adminTrial → adminMonthly internally
        plan_name = 'adminMonthly' if raw_plan_name == 'adminTrial' else raw_plan_name

        try:
            plan = Plan.objects.get(name=plan_name)
        except Plan.DoesNotExist:
            print(f"❌ Plan not found for: {plan_name}")
            return HttpResponse(status=500)

        try:
            PendingSignup.objects.create(
                email=customer_email,
                session_id=session_id,
                token=token,
                plan=raw_plan_name,  # Keep original for clarity in admin view
                subscription_id=subscription_id
            )
            print(f"✅ PendingSignup saved for {customer_email}")

            registration_link = f"http://localhost:3000/admin_register?token={token}"
            print("\n" + "=" * 60)
            print("📩 Registration email (simulated):")
            print(f"To: {customer_email}")
            print("Subject: Finish setting up your Admin Account")
            print(f"➡️ Click to register:\n{registration_link}")
            print("=" * 60 + "\n")

        except Exception as e:
            print(f"❌ Error saving PendingSignup: {str(e)}")
            return HttpResponse(status=500)

    return HttpResponse(status=200)
