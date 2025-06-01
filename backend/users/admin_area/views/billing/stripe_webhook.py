import stripe
import json

from django.conf import settings
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from django.utils.crypto import get_random_string
from users.admin_area.models import PreCheckoutEmail
from users.admin_area.utils.history_creator import log_history_event
from users.admin_area.utils import (
    log_transaction_event,
    log_history_event,
    log_pendingsignup_event)

stripe.api_key = settings.STRIPE_SECRET_KEY
endpoint_secret = settings.STRIPE_WEBHOOK_SECRET


@csrf_exempt
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
        # Fallback transaction ID
        stripe_transaction_id = session.get('invoice')

        # Fallback if email missing
        if not customer_email:
            customer_id = session.get('customer')
            if customer_id:
                customer = stripe.Customer.retrieve(customer_id)
                customer_email = customer.get('email')

        print(f"🔍 Webhook triggered for session: {session_id}")
        print(f"📧 Email: {customer_email}")

        # Metadata from checkout creation
        raw_plan_name = session.get('metadata', {}).get('plan_name')
        if not raw_plan_name:
            print("❌ Missing plan_name in metadata")
            return HttpResponse(status=500)

        # Normalize: adminTrial → adminMonthly internally
        plan_name = 'adminMonthly' if raw_plan_name == 'adminTrial' else raw_plan_name

        log_history_event(
            email=customer_email,  
            event_type='stripe_payment', 
            plan_name=plan_name, 
            stripe_transaction_id=stripe_transaction_id, 
            payment_processed_on=timezone.now()
        )


        # ✅ Remove from PreCheckoutEmail table
        PreCheckoutEmail.objects.filter(email=customer_email).delete()

        # ✅ Log to separate transaction log model
        log_transaction_event(
            email=customer_email, 
            stripe_transaction_id=stripe_transaction_id
        )
        token = get_random_string(64)
        log_pendingsignup_event(
            email=customer_email,
            token=token,
            session_id=session_id,
            plan_name=plan_name,
            stripe_transaction_id=stripe_transaction_id
        )
        registration_link = f"http://localhost:3000/admin_register?token={token}"
        print("\n" + "=" * 60)
        print("📩 Registration email (simulated):")
        print(f"To: {customer_email}")
        print("Subject: Finish setting up your Admin Account")
        print(f"➡️ Click to register:\n{registration_link}")
        print("=" * 60 + "\n")

    return HttpResponse(status=200)
