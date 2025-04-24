import stripe
from django.http import HttpResponse
from django.utils.crypto import get_random_string
from django.utils import timezone
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from adminplans.models import AdminPlan, AdminPendingSignup
from users.models import CustomUser

# Stripe configuration
stripe.api_key = settings.STRIPE_SECRET_KEY
endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

@api_view(['POST'])
@permission_classes([AllowAny])  # Stripe must hit this anonymously
def admin_stripe_webhook(request):
    token = get_random_string(length=64)  # One-time-use registration token
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    # ✅ Verify webhook signature
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        print("❌ Signature verification failed")
        return HttpResponse(status=400)

    # 🎯 Listen for checkout completion only
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        session_id = session.get('id')
        customer_email = session.get('customer_email')
        subscription_id = session.get('subscription')

        # Fallback to retrieve email from customer object if missing
        if not customer_email:
            customer_id = session.get('customer')
            if customer_id:
                customer = stripe.Customer.retrieve(customer_id)
                customer_email = customer.get('email')

        print(f"📥 New signup webhook: {customer_email}, session: {session_id}")

        # Get plan metadata
        raw_plan_name = session.get('metadata', {}).get('plan_name')
        if not raw_plan_name:
            print("❌ Missing plan_name in metadata")
            return HttpResponse(status=500)

        # Normalize trial to use monthly plan ID logic internally
        plan_name = 'adminMonthly' if raw_plan_name == 'adminTrial' else raw_plan_name

        try:
            # Confirm the plan exists in DB
            plan = AdminPlan.objects.get(name=plan_name)
        except AdminPlan.DoesNotExist:
            print(f"❌ AdminPlan not found: {plan_name}")
            return HttpResponse(status=500)

        # 🚫 If the user already exists, this is NOT a new signup → ignore
        if CustomUser.objects.filter(email=customer_email).exists():
            print(f"⚠️ User already exists: {customer_email} — skipping signup webhook")
            return HttpResponse(status=200)

        try:
            # ✅ Create a new pending signup for this email + session
            AdminPendingSignup.objects.create(
                email=customer_email,
                session_id=session_id,
                token=token,
                plan=raw_plan_name,
                subscription_id=subscription_id
            )
            print(f"✅ AdminPendingSignup created for {customer_email}")

            # ✉️ Simulated registration link
            registration_link = f"http://localhost:3000/admin_register?token={token}"
            print("\n" + "=" * 60)
            print("📩 Registration email (simulated):")
            print(f"To: {customer_email}")
            print(f"➡️ Click to register: {registration_link}")
            print("=" * 60 + "\n")

        except Exception as e:
            print(f"❌ Error creating AdminPendingSignup: {e}")
            return HttpResponse(status=500)

    return HttpResponse(status=200)
