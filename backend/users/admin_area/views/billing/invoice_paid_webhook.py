import stripe
from django.http import HttpResponse
from django.conf import settings
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from core.models import CustomUser
from users.admin_area.models import Plan, Profile, AccountHistory, ScheduledSubscription
from users.admin_area.utils.account_logger import log_account_event
from users.admin_area.utils.scheduled_subscription_logger import create_scheduled_subscription

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

    if event['type'] != 'invoice.paid':
        return HttpResponse(status=200)

    invoice = event['data']['object']
    subscription_id = invoice.get('subscription')
    customer_id = invoice.get('customer')
    charge_id = invoice.get('charge')
    email = invoice.get('customer_email')

    print("💳 Invoice Paid Webhook Triggered")
    print(f"📧 Email: {email or '[unknown]'}")
    print(f"🧾 Subscription ID: {subscription_id}")
    print(f"💰 Charge ID: {charge_id}")

    transaction_id = None
    if charge_id:
        try:
            charge_obj = stripe.Charge.retrieve(charge_id)
            transaction_id = charge_obj.get('id')
        except Exception as e:
            print(f"⚠️ Could not fetch charge object: {e}")

    # Resolve Plan
    plan = None
    plan_name = "unknown_plan"
    try:
        price_id = invoice.get("lines", {}).get("data", [{}])[0].get("price", {}).get("id")
        if price_id:
            plan = Plan.objects.get(stripe_price_id=price_id)
            plan_name = plan.name
    except Exception as e:
        print(f"⚠️ Failed to resolve plan from invoice: {e}")
        return HttpResponse(status=500)

    # Reactivation metadata
    reactivation_type = None
    user_id = None
    try:
        subscription = stripe.Subscription.retrieve(subscription_id)
        metadata = subscription.get("metadata", {})
        reactivation_type = metadata.get("reactivation_type")
        user_id = metadata.get("user_id")
    except Exception as e:
        print(f"⚠️ Could not retrieve metadata: {e}")

    if reactivation_type == "immediate":
        try:
            user = CustomUser.objects.get(id=user_id)
            profile = user.profiles.get(is_current=True)
        except CustomUser.DoesNotExist:
            print(f"❌ No user found for ID: {user_id}")
            return HttpResponse(status=400)
        except Profile.DoesNotExist:
            print(f"❌ No current profile found for user: {user.email}")
            return HttpResponse(status=400)

        if user.subscription_status == "admin_trial" and profile.is_canceled:
            if profile.subscription_end_date and profile.subscription_end_date > timezone.now():
                # ⏳ Schedule activation after trial ends
                create_scheduled_subscription(
                    user=user,
                    plan=plan,
                    starts_on=profile.subscription_end_date,
                    stripe_subscription_id=subscription_id,
                    stripe_transaction_id=transaction_id
                )
                print(f"📅 ScheduledSubscription created for {user.email} on {profile.subscription_end_date}")

                log_account_event(
                    event_type="scheduled_reactivation",
                    email=user.email,
                    plan_name=plan.name,
                    stripe_customer_id=customer_id,
                    stripe_subscription_id=subscription_id,
                    stripe_transaction_id=transaction_id,
                    subscription_start=profile.subscription_end_date
                )
                return HttpResponse(status=200)

        # Log as fallback reactivation payment
        log_account_event(
            event_type='stripe_payment',
            email=user.email,
            plan_name=plan_name,
            stripe_customer_id=customer_id,
            stripe_subscription_id=subscription_id,
            stripe_transaction_id=transaction_id,
            payment_processed_on=timezone.now()
        )
        print(f"🧾 Reactivation payment logged for {user.email}")
        return HttpResponse(status=200)

    # Default (non-reactivation) logging
    if email:
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
            print(f"🧾 Payment logged for: {email}")
        except Exception as e:
            print(f"❌ Failed to log payment: {e}")

    # ✅ Final fallback to avoid 500 errors
    return HttpResponse(status=200)
