import stripe
import json

from django.conf import settings
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.utils.crypto import get_random_string
from django.contrib.auth import get_user_model

from users.admin_area.models import PreCheckoutEmail, Profile, EventTracker, AdminIdentity
from users.admin_area.utils import (
    log_transaction_event,
    log_pendingsignup_event
)

stripe.api_key = settings.STRIPE_SECRET_KEY
endpoint_secret = settings.STRIPE_WEBHOOK_SECRET


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        print("❌ Signature verification failed")
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        metadata = session.get("metadata", {})
        session_id = session.get('id')
        stripe_transaction_id = session.get('invoice')

        # ✅ Consistent and safe email retrieval
        email = session.get('customer_email')
        if not email:
            customer_id = session.get('customer')
            try:
                customer = stripe.Customer.retrieve(customer_id)
                email = customer.get("email")
            except Exception as e:
                print(f"❌ Error retrieving customer: {e}")
                return HttpResponse(status=500)

        if not email:
            print("❌ Email could not be determined — aborting")
            return HttpResponse(status=500)

        print(f"🔍 Webhook triggered for session: {session_id}")
        print(f"📧 Email: {email}")

        # ✅ Get plan and trial info from metadata
        raw_plan_name = metadata.get('plan_name')
        is_trial = str(metadata.get('is_trial', '')).strip().lower() in ('true', '1', 'yes', 'y', 't')

        if not raw_plan_name:
            print("❌ Missing plan_name in metadata")
            return HttpResponse(status=500)

        # Normalize trial alias
        plan_name = 'adminMonthly' if raw_plan_name == 'adminTrial' else raw_plan_name

        # ✅ Get AdminIdentity for email
        try:
            admin_identity = AdminIdentity.objects.get(admin_email=email)
        except AdminIdentity.DoesNotExist:
            print(f"❌ AdminIdentity not found for {email}")
            return HttpResponse(status=500)

        # ✅ Log EventTracker entry for stripe_purchase
        EventTracker.objects.create(
            admin=admin_identity,
            event_type='stripe_purchase',
            details=f"Session: {session_id} | Plan: {plan_name} | Trial: {is_trial}"
        )

        PreCheckoutEmail.objects.filter(admin__admin_email=email).delete()


        # ✅ Log transaction
        log_transaction_event(
            email=email,
            stripe_transaction_id=stripe_transaction_id
        )

        # ✅ Create pending signup + simulate email
        token = get_random_string(64)
        log_pendingsignup_event(
            email=email,
            token=token,
            session_id=session_id,
            plan_name=plan_name,
            is_trial=is_trial,
            stripe_transaction_id=stripe_transaction_id,
            created_at=timezone.now()
        )

        registration_link = f"http://localhost:3000/admin_register?token={token}"
        print("\n" + "=" * 60)
        print("📩 Registration email (simulated):")
        print(f"To: {email}")
        print("Subject: Finish setting up your Admin Account")
        print(f"➡️ Click to register:\n{registration_link}")
        print("=" * 60 + "\n")

    elif event['type'] == 'invoice.paid':
        invoice = event['data']['object']
        subscription_id = invoice.get('subscription')
        stripe_transaction_id = invoice.get('id')
        customer_id = invoice.get('customer')

        email = None
        try:
            customer = stripe.Customer.retrieve(customer_id)
            email = customer.get('email')
        except Exception as e:
            print(f"❌ Error retrieving customer: {e}")
            return HttpResponse(status=500)

        if not email:
            print("❌ Could not find email during invoice.paid")
            return HttpResponse(status=500)

        print(f"📦 invoice.paid webhook for {email} | Stripe Sub: {subscription_id}")

        User = get_user_model()

        profile = Profile.objects.filter(user__email=email, is_active=True, is_canceled=False).first()
        if profile:
            next_billing_unix = invoice.get('lines', {}).get('data', [{}])[0].get('period', {}).get('end')
            if next_billing_unix:
                from datetime import datetime
                next_billing_date = datetime.fromtimestamp(next_billing_unix)
                profile.next_billing = next_billing_date
                profile.stripe_transaction_id = stripe_transaction_id
                profile.save()
            else:
                print(f"⚠️ No next_billing period found in invoice for {email}")

            log_transaction_event(email=email, stripe_transaction_id=stripe_transaction_id)
        else:
            print(f"⚠️ No active profile found for {email}. Could be canceled or missing.")

    return HttpResponse(status=200)
