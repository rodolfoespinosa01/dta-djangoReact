import stripe
from django.http import HttpResponse
from django.conf import settings
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from users.admin_area.models import Plan
from users.admin_area.utils.account_logger import log_account_event

stripe.api_key = settings.STRIPE_SECRET_KEY
endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

@api_view(['POST'])
@permission_classes([AllowAny])
def invoice_paid_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        print("❌ Signature verification failed")
        return HttpResponse(status=400)

    if event['type'] == 'invoice.paid':
        invoice = event['data']['object']
        subscription_id = invoice.get('subscription')
        customer_id = invoice.get('customer')
        charge_id = invoice.get('charge')
        email = invoice.get('customer_email') or invoice.get('customer', {}).get('email')

        print(f"💳 Invoice Paid Webhook Triggered")
        print(f"📧 Email: {email or '[unknown]'}")
        print(f"🧾 Subscription ID: {subscription_id}")
        print(f"💰 Charge ID (transaction): {charge_id}")

        # Get the actual Stripe charge object if charge_id is present
        transaction_id = None
        if charge_id:
            try:
                charge_obj = stripe.Charge.retrieve(charge_id)
                transaction_id = charge_obj.get('id')
            except Exception as e:
                print(f"⚠️ Could not fetch charge object: {e}")

        # Determine the plan name from invoice line items
        plan_name = "unknown_plan"
        try:
            price_id = invoice.get("lines", {}).get("data", [{}])[0].get("price", {}).get("id")
            if price_id:
                plan = Plan.objects.get(stripe_price_id=price_id)
                plan_name = plan.name
        except Exception as e:
            print(f"⚠️ Failed to resolve plan name from invoice: {str(e)}")

        try:
            log_account_event(
                event_type='stripe_payment',
                email=email,
                plan_name=plan_name,
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
                stripe_transaction_id=transaction_id,
                payment_processed_on=timezone.now()
            )
            print("🧾 Stripe payment logged to account history.")
        except Exception as e:
            print(f"❌ Failed to log account history in invoice.paid: {str(e)}")

    return HttpResponse(status=200)
