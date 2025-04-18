from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.crypto import get_random_string
from django.conf import settings
import stripe

from adminplans.models import AdminPlan, AdminProfile, PendingAdminSignup
from users.models import CustomUser

endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
stripe.api_key = settings.STRIPE_SECRET_KEY

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

    # ✅ Admin plan signup via checkout
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        session_id = session.get('id')
        customer_email = session.get('customer_email')
        subscription_id = session.get('subscription')

        if not customer_email:
            customer_id = session.get('customer')
            if customer_id:
                customer = stripe.Customer.retrieve(customer_id)
                customer_email = customer.get('email')

        plan_name = session.get('metadata', {}).get('plan_name')
        actual_plan_name = 'adminMonthly' if plan_name == 'adminTrial' else plan_name

        print(f"🔍 Webhook (checkout.session.completed): {session_id}")
        print(f"📧 Email: {customer_email} | 🧾 Subscription ID: {subscription_id} | 🪪 Plan: {plan_name}")

        try:
            plan = AdminPlan.objects.get(name=actual_plan_name)
        except AdminPlan.DoesNotExist:
            print(f"❌ AdminPlan not found for: {actual_plan_name}")
            return HttpResponse(status=500)

        try:
            PendingAdminSignup.objects.create(
                email=customer_email,
                session_id=session_id,
                token=token,
                plan=plan_name,
                subscription_id=subscription_id
            )

            registration_link = f"http://localhost:3000/admin-register?token={token}"
            print("=" * 60)
            print("📩 Registration Email (Simulated):")
            print(f"To: {customer_email}")
            print("Subject: Finish setting up your Admin Account")
            print(f"➡️ Register here:\n{registration_link}")
            print("=" * 60)

        except Exception as e:
            print(f"❌ Error saving PendingAdminSignup: {str(e)}")
            return HttpResponse(status=500)

    # ✅ Subscription paid successfully
    elif event['type'] == 'invoice.paid':
        invoice = event['data']['object']
        subscription_id = invoice.get('subscription')
        customer_id = invoice.get('customer')

        print(f"💰 invoice.paid → Subscription ID: {subscription_id}")

        # (Optional: future logic to track payments, invoice receipts, etc.)

    # ✅ Subscription cancelled (immediately or after trial)
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        subscription_id = subscription.get('id')
        customer_id = subscription.get('customer')

        print(f"❌ Subscription cancelled → Subscription ID: {subscription_id}")

        profile = AdminProfile.objects.filter(admin_stripe_subscription_id=subscription_id).first()
        if profile:
            user = profile.user
            user.subscription_status = 'admin_inactive'
            user.save()

            profile.auto_renew_cancelled = True
            profile.next_billing_date = None
            profile.save()

            print(f"⚠️ Admin {user.email} marked as inactive (cancellation confirmed).")

    return HttpResponse(status=200)
