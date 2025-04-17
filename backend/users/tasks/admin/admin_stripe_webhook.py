from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.crypto import get_random_string
from django.conf import settings
import stripe

from adminplans.models import AdminPlan, PendingAdminSignup

endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

@csrf_exempt
def admin_stripe_webhook(request):
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
        subscription_id = session.get('subscription')  # ✅ Extract subscription ID for paid plans

        # Fallback for missing email
        if not customer_email:
            customer_id = session.get('customer')
            if customer_id:
                customer = stripe.Customer.retrieve(customer_id)
                customer_email = customer.get('email')

        print(f"🔍 Webhook triggered for session: {session_id}")
        print(f"📧 Email: {customer_email}")
        print(f"🧾 Subscription ID: {subscription_id}")

        plan_name = session.get('metadata', {}).get('plan_name')
        if not plan_name:
            print("❌ Missing plan name in session metadata")
            return HttpResponse(status=500)

        try:
            plan = AdminPlan.objects.get(name=plan_name)
        except AdminPlan.DoesNotExist:
            print(f"❌ AdminPlan not found for: {plan_name}")
            return HttpResponse(status=500)

        try:
            PendingAdminSignup.objects.create(
                email=customer_email,
                session_id=session_id,
                token=token,
                plan=plan_name,
                subscription_id=subscription_id  # ✅ Store it here
            )
            print(f"✅ PendingAdminSignup saved for {customer_email}")

            registration_link = f"http://localhost:3000/admin-register?token={token}"
            print("\n" + "=" * 60)
            print("📩 Registration email (simulated):")
            print(f"To: {customer_email}")
            print("Subject: Finish setting up your Admin Account")
            print("Body:")
            print(f"➡️ Click to register:\n{registration_link}")
            print("=" * 60 + "\n")

        except Exception as e:
            print(f"❌ Error saving PendingAdminSignup: {str(e)}")
            return HttpResponse(status=500)

    return HttpResponse(status=200)