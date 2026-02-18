import json
import stripe
from datetime import datetime
from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model

from users.admin_area.models import (
    PreCheckout,
    Profile,
    EventTracker,
    AdminIdentity,
    TransactionLog,
)
from users.admin_area.utils import (
    log_TransactionLog,
    log_PendingSignup,
)

stripe.api_key = settings.STRIPE_SECRET_KEY
endpoint_secret = settings.STRIPE_WEBHOOK_SECRET


def _ts_to_aware(ts: int | None):
    if not ts:
        return None
    # Stripe timestamps are seconds since epoch (UTC)
    return timezone.make_aware(datetime.utcfromtimestamp(ts))


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        print("❌ Signature verification failed")
        return HttpResponse(status=400)

    etype = event.get('type')
    obj = event['data']['object']

    # ============================================================
    # 1) After Checkout completes: create PendingSignup + link
    # ============================================================
    if etype == 'checkout.session.completed':
        session = obj
        metadata = session.get("metadata", {}) or {}
        is_reactivation = str(metadata.get("reactivation", "")).strip() == "1"

        # email: prefer session.customer_email, fallback to customer object
        email = session.get('customer_email')
        if not email:
            customer_id = session.get('customer')
            try:
                customer = stripe.Customer.retrieve(customer_id)
                email = customer.get('email')
            except Exception as e:
                print(f"❌ Error retrieving customer: {e}")
                return HttpResponse(status=500)

        if not email:
            print("❌ Email could not be determined — aborting")
            return HttpResponse(status=200)

        session_id = session.get('id')
        stripe_transaction_id = session.get('invoice')  # may be None until first charge
        raw_plan_name = metadata.get('plan_name') or ''
        is_trial = str(metadata.get('is_trial', '')).strip().lower() in ('true', '1', 'yes', 'y', 't')

        # normalize if you had an older alias
        plan_name = 'adminMonthly' if raw_plan_name == 'adminTrial' else raw_plan_name

        User = get_user_model()
        is_existing_user = User.objects.filter(email=email).exists()

        # Ensure AdminIdentity exists for this email (per your model rules)
        try:
            admin_identity = AdminIdentity.objects.get(admin_email=email)
        except AdminIdentity.DoesNotExist:
            admin_identity = AdminIdentity.objects.create(admin_email=email)

        # Track the purchase intent
        EventTracker.objects.create(
            admin=admin_identity,
            event_type='stripe_purchase',
            details=f"Session: {session_id} | Plan: {plan_name} | Trial: {is_trial}"
        )

        # Remove any pre‑checkout placeholder rows
        PreCheckout.objects.filter(admin__admin_email=email).delete()

        # Idempotent: only log if we haven't already seen this invoice id
        if stripe_transaction_id and not TransactionLog.objects.filter(
            stripe_transaction_id=stripe_transaction_id
        ).exists():
            log_TransactionLog(email=email, stripe_transaction_id=stripe_transaction_id)


        # Registration link should only be sent on the initial purchase path.
        if is_reactivation or is_existing_user:
            EventTracker.objects.create(
                admin=admin_identity,
                event_type='checkout_completed_no_registration_link',
                details=f"Session: {session_id} | Reactivation: {is_reactivation} | ExistingUser: {is_existing_user}"
            )
            return HttpResponse(status=200)

        # Initial registration flow only:
        # Create PendingSignup and "send" registration link (console)
        token = get_random_string(64)
        log_PendingSignup(
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

        # Done. Stripe only needs a 2xx.
        return HttpResponse(status=200)

    # ============================================================
    # 2) When an invoice is paid (first charge after trial, renewals)
    #    → flip out of trial, set subscription_start, next_billing
    # ============================================================
    if etype == 'invoice.paid':
        invoice = obj
        subscription_id = invoice.get('subscription')
        stripe_transaction_id = invoice.get('id')
        customer_id = invoice.get('customer')

        # Determine email (prefer subscription metadata if you add it there; fallback to customer)
        email = None
        try:
            cust = stripe.Customer.retrieve(customer_id)
            email = cust.get('email')
        except Exception as e:
            print(f"❌ Error retrieving customer: {e}")
            return HttpResponse(status=500)

        if not email:
            print("❌ Could not find email during invoice.paid")
            return HttpResponse(status=200)

        print(f"📦 invoice.paid for {email} | Stripe Sub: {subscription_id}")

        # Load the subscription to get current period end and cancel flags
        try:
            sub = stripe.Subscription.retrieve(subscription_id)
        except Exception as e:
            print(f"❌ Error retrieving subscription: {e}")
            return HttpResponse(status=200)

        current_period_end = _ts_to_aware(sub.get('current_period_end'))
        cancel_at_period_end = bool(sub.get('cancel_at_period_end'))

        # Paid timestamp (prefer paid_at; fallback to invoice.created)
        paid_at = (invoice.get('status_transitions') or {}).get('paid_at') or invoice.get('created')
        paid_dt = _ts_to_aware(paid_at)

        # Update Profile if user already registered and an active profile exists
        User = get_user_model()
        profile = Profile.objects.filter(user__email=email, is_active=True).first()

        if profile:
            # First successful charge stamps subscription_start if missing
            if profile.subscription_start is None:
                profile.subscription_start = paid_dt

            # Flip out of trial and set billing markers
            profile.is_trial = False
            profile.subscription_active = True
            profile.subscription_end = None  # active sub has no end date
            profile.next_billing = current_period_end
            profile.is_canceled = cancel_at_period_end

            # Optionally store the invoice id for reference
            profile.stripe_transaction_id = stripe_transaction_id

            profile.save()
        else:
            print(f"⚠️ No active profile found for {email}. They may not have registered yet.")

        # Idempotent logging: only once per invoice id
        if stripe_transaction_id and not TransactionLog.objects.filter(
            stripe_transaction_id=stripe_transaction_id
        ).exists():
            log_TransactionLog(email=email, stripe_transaction_id=stripe_transaction_id)

        return HttpResponse(status=200)

   # ============================================================
    # 3) Keep flags in sync on subscription updates
    #    - While active/trialing: keep is_active = True
    #    - When Stripe cancels at period end: lock access (is_active=False)
    # ============================================================
    if etype == 'customer.subscription.updated':
        sub = obj
        customer_id = sub.get('customer')
        email = None
        try:
            cust = stripe.Customer.retrieve(customer_id)
            email = cust.get('email')
        except Exception:
            return HttpResponse(status=200)
        if not email:
            return HttpResponse(status=200)

        status_val = sub.get('status')  # 'trialing' | 'active' | 'canceled' | ...
        sub_id = sub.get('id')
        current_period_end = _ts_to_aware(sub.get('current_period_end'))
        cancel_at_period_end = bool(sub.get('cancel_at_period_end'))
        ended_at = _ts_to_aware(sub.get('ended_at'))

        profile = Profile.objects.filter(user__email=email, is_active=True).first() or \
                Profile.objects.filter(user__email=email).first()
        if not profile:
            return HttpResponse(status=200)

        # --- ENFORCE auto_renew <-> cancel_at_period_end ---
        desired_cancel = (profile.auto_renew is False)  # True means we want to cancel at period end
        if status_val in ('trialing', 'active') and desired_cancel != cancel_at_period_end:
            try:
                sub = stripe.Subscription.modify(sub_id, cancel_at_period_end=desired_cancel)
                cancel_at_period_end = bool(sub.get('cancel_at_period_end'))
                current_period_end = _ts_to_aware(sub.get('current_period_end'))
            except Exception as e:
                print(f"⚠️ Enforcement failed for {email}: {e}")

        # Mirror Stripe to DB after enforcement
        profile.auto_renew = not cancel_at_period_end

        if status_val == 'canceled':
            profile.is_trial = False
            profile.is_canceled = True
            profile.subscription_active = False
            profile.subscription_end = ended_at or profile.subscription_end or timezone.now()
            profile.next_billing = None
            profile.is_active = False  # lock access at actual end
        else:
            profile.subscription_active = status_val in ('trialing', 'active')
            if status_val != 'trialing':
                profile.is_trial = False
            if cancel_at_period_end:
                # Scheduled to end: keep access, show end date, no next billing
                if not profile.subscription_end:
                    profile.subscription_end = current_period_end
                profile.next_billing = None
                profile.is_active = True
            else:
                # Auto-renew on: reset end date, keep next_billing from Stripe
                profile.subscription_end = None
                profile.next_billing = current_period_end
                profile.is_active = True

        profile.save()
        return HttpResponse(status=200)



    # Ignore other events for now
    return HttpResponse(status=200)
