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
from users.admin_area.utils.log_EventTracker import log_EventTracker

stripe.api_key = settings.STRIPE_SECRET_KEY
endpoint_secret = settings.STRIPE_WEBHOOK_SECRET


def _ts_to_aware(ts: int | None):
    if not ts:
        return None
    # Stripe timestamps are seconds since epoch (UTC)
    return timezone.make_aware(datetime.utcfromtimestamp(ts))

<<<<<<< HEAD
=======
def _stripe_customer_id_by_email(email: str) -> str | None:
    try:
        res = stripe.Customer.list(email=email, limit=1)
        if res and res.data:
            return res.data[0].id
    except Exception:
        pass
    return None

def _active_subscription_id_for_email(email: str) -> str | None:
    cust_id = _stripe_customer_id_by_email(email)
    if not cust_id:
        return None
    try:
        subs = stripe.Subscription.list(customer=cust_id, status="active", limit=1)
        if subs and subs.data:
            return subs.data[0].id
    except Exception:
        pass
    return None

def _is_reactivation_session(session: dict) -> bool:
    md = session.get("metadata") or {}
    return str(md.get("reactivation", "")).strip() == "1"

def _subscription_has_reactivation_meta(sub_id: str | None) -> bool:
    if not sub_id:
        return False
    try:
        sub = stripe.Subscription.retrieve(sub_id)
        return (sub.get("metadata") or {}).get("reactivation") == "1"
    except Exception:
        return False

def _plan_from_price_id(price_id: str | None):
    if not price_id:
        return None
    try:
        return Plan.objects.get(stripe_price_id=price_id)
    except Plan.DoesNotExist:
        return None

def _user_from_admin_id(admin_id: str):
    if not admin_id:
        return None
    try:
        ident = AdminIdentity.objects.get(adminID=admin_id)
    except AdminIdentity.DoesNotExist:
        return None
    return get_user_model().objects.filter(email=ident.admin_email).first()

def _active_subscription_id_for_admin_id(admin_id: str) -> str | None:
    # Prefer Search API by metadata (fast, robust). Falls back to email.
    try:
        custs = stripe.Customer.search(query=f"metadata['admin_id']:'{admin_id}'", limit=1)
        if custs and custs.data:
            subs = stripe.Subscription.list(customer=custs.data[0].id, status="active", limit=1)
            if subs and subs.data:
                return subs.data[0].id
    except Exception:
        pass
    try:
        ident = AdminIdentity.objects.get(adminID=admin_id)
        custs = stripe.Customer.list(email=ident.admin_email, limit=1)
        if custs and custs.data:
            subs = stripe.Subscription.list(customer=custs.data[0].id, status="active", limit=1)
            if subs and subs.data:
                return subs.data[0].id
    except Exception:
        pass
    return None

def _log_admin_event(email: str | None, event_type: str, details: str = ""):
    if not email:
        return
    try:
        log_EventTracker(admin_email=email, event_type=event_type, details=details)
    except Exception:
        pass

def _subscription_status_from_plan_name(plan_name: str | None) -> str:
    mapping = {
        "adminMonthly": "admin_monthly",
        "adminQuarterly": "admin_quarterly",
        "adminAnnual": "admin_annual",
    }
    return mapping.get(plan_name or "")

def _cancel_other_trialing_subscriptions(customer_id: str | None, keep_sub_id: str | None):
    if not customer_id:
        return
    try:
        subs = stripe.Subscription.list(customer=customer_id, status="all", limit=100)
    except Exception:
        return

    for sub in (subs.data or []):
        sid = sub.get("id")
        if sid == keep_sub_id:
            continue
        if sub.get("status") == "trialing":
            try:
                stripe.Subscription.delete(sid)
            except Exception:
                pass


# ------------------------ webhook ------------------------
>>>>>>> f5fcba9 (Added Codex, working on upgrade, cancel, and reactivation flow)

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
<<<<<<< HEAD
    # 1) After Checkout completes: create PendingSignup + link
=======
    # REACTIVATION: checkout.session.completed (metadata.reactivation == "1")
    # ============================================================
    if etype == 'checkout.session.completed' and _is_reactivation_session(obj):
        session = obj
        md = session.get("metadata") or {}
        admin_id = md.get("admin_id")
        target_plan_name = md.get("target_plan_name")

        # Resolve email
        email = md.get("admin_email") or session.get('customer_email')
        if not email and session.get('customer'):
            try:
                email = stripe.Customer.retrieve(session['customer']).get('email')
            except Exception:
                email = None
        if not email:
            return HttpResponse(status=200)

        # Minimal TX log (email + tx id)
        tx_id = session.get('payment_intent') or session.get('invoice')
        if tx_id:
            log_TransactionLog(email=email, stripe_transaction_id=tx_id)
            _log_admin_event(email, "reactivation_checkout_completed", f"tx_id={tx_id}")

        # New subscription created by Checkout (we may cancel it if user already active)
        new_sub_id = session.get('subscription')
        new_price_id, new_period_end = None, None
        try:
            if new_sub_id:
                sub = stripe.Subscription.retrieve(new_sub_id, expand=["items.data.price"])
                items = (sub.get("items") or {}).get("data") or []
                if items:
                    new_price_id = items[0]["price"]["id"]
                new_period_end = sub.get("current_period_end")
        except Exception:
            pass
        plan = _plan_from_price_id(new_price_id)
        if not plan and target_plan_name:
            plan = Plan.objects.filter(name=target_plan_name).first()

        # Find the Django user and their active profile
        user = get_user_model().objects.filter(email=email).first()
        active = Profile.objects.filter(user__email=email, is_active=True).first()

        # If currently trialing, upgrade should be immediate:
        # end trial now, activate paid plan now, and cancel old trial subscription(s).
        if user and active and bool(getattr(active, "is_trial", False)):
            now_dt = timezone.now()
            Profile.objects.filter(user=user, is_active=True).update(
                is_active=False,
                subscription_end=now_dt,
                is_canceled=False,
            )
            Profile.objects.create(
                user=user,
                plan=plan,
                is_active=True,
                is_canceled=False,
                is_trial=False,
                subscription_start=now_dt,
                subscription_end=None,
                next_billing=_ts_to_aware(new_period_end),
            )
            resolved_status = _subscription_status_from_plan_name(getattr(plan, "name", None))
            if resolved_status:
                user.subscription_status = resolved_status
                user.save(update_fields=["subscription_status"])

            _cancel_other_trialing_subscriptions(session.get("customer"), new_sub_id)
            _log_admin_event(
                email,
                "trial_converted_to_paid_immediate",
                f"new_price_id={new_price_id or ''} new_sub_id={new_sub_id or ''}"
            )
            return HttpResponse(status=200)

        # Not active → create a brand-new ACTIVE Profile now
        if user and not active:
            Profile.objects.filter(user=user).update(is_active=False)  # enforce single active
            Profile.objects.create(
                user=user,
                plan=plan,
                is_active=True,
                is_canceled=False,
                is_trial=False,
                subscription_start=None,                 # set on first invoice.paid
                subscription_end=None,
                next_billing=_ts_to_aware(new_period_end),
            )
            _log_admin_event(
                email,
                "plan_change_applied_immediate",
                f"reason=no_active_profile new_price_id={new_price_id or ''}"
            )
            return HttpResponse(status=200)

        # Already active → schedule upgrade at end of current term
        # Prefer lookup by admin_id in Stripe; fallback to email
        current_sub_id = _active_subscription_id_for_admin_id(admin_id) or _active_subscription_id_for_email(email)
        if not current_sub_id:
            # Fallback: immediate switch to new plan (no schedule available)
            if active:
                Profile.objects.filter(pk=active.pk).update(is_active=False)
                Profile.objects.create(
                    user=active.user,
                    plan=plan,
                    is_active=True,
                    is_canceled=False,
                    is_trial=False,
                    next_billing=_ts_to_aware(new_period_end),
                )
                _log_admin_event(
                    email,
                    "plan_change_applied_immediate",
                    f"reason=no_current_sub new_price_id={new_price_id or ''}"
                )
            return HttpResponse(status=200)

        # Tag the existing sub so later events can detect reactivation path (optional)
        try:
            existing = stripe.Subscription.retrieve(current_sub_id)
            tag_md = (existing.get("metadata") or {})
            tag_md.update({"reactivation": "1", "reactivation_price": new_price_id or "", "admin_id": admin_id or ""})
            stripe.Subscription.modify(current_sub_id, metadata=tag_md)
        except Exception:
            pass

        # Read existing sub to get current period end and current price
        try:
            current_sub = stripe.Subscription.retrieve(current_sub_id, expand=["items.data.price"])
            curr_end = current_sub.get("current_period_end")
            curr_items = (current_sub.get("items") or {}).get("data") or []
            curr_price_id = curr_items[0]["price"]["id"] if curr_items else None
        except Exception:
            return HttpResponse(status=200)

        # Create a schedule: keep current price until curr_end, then switch to new price
        try:
            phases = []
            now_ts = int(timezone.now().timestamp())
            if curr_price_id and curr_end and curr_end > now_ts:
                phases.append({
                    "items": [{"price": curr_price_id, "quantity": 1}],
                    "start_date": "now",
                    "end_date": curr_end,
                })
            phases.append({"items": [{"price": new_price_id, "quantity": 1}]})
            stripe.SubscriptionSchedule.create(
                from_subscription=current_sub_id,
                phases=phases,
                metadata={"reactivation_schedule": "1", "admin_id": admin_id or ""},
            )
            _log_admin_event(
                email,
                "plan_change_scheduled",
                f"from_price_id={curr_price_id or ''} to_price_id={new_price_id or ''} effective_at={curr_end or ''}"
            )
        except Exception:
            return HttpResponse(status=200)

        # Cancel the duplicate (checkout) subscription to avoid double-billing
        try:
            if new_sub_id and new_sub_id != current_sub_id:
                stripe.Subscription.delete(new_sub_id)
        except Exception:
            pass

        # Upsert a single pending (inactive) Profile that will start at curr_end
        pending = Profile.objects.filter(user__email=email, is_active=False).first()
        if pending:
            pending.plan = plan
            pending.subscription_start = _ts_to_aware(curr_end)  # when it will become active
            pending.is_trial = False
            pending.is_canceled = False
            pending.save()
            _log_admin_event(
                email,
                "plan_change_pending_profile_upserted",
                f"effective_at={curr_end or ''} mode=update"
            )
        else:
            if user:
                Profile.objects.create(
                    user=user,
                    plan=plan,
                    is_active=False,                     # pending
                    is_trial=False,
                    is_canceled=False,
                    subscription_start=_ts_to_aware(curr_end),
                    next_billing=None,
                )
                _log_admin_event(
                    email,
                    "plan_change_pending_profile_upserted",
                    f"effective_at={curr_end or ''} mode=create"
                )

        return HttpResponse(status=200)

    # ============================================================
    # GENERAL: checkout.session.completed (no reactivation flag)
    # (Your original flow: create PendingSignup + registration link)
>>>>>>> f5fcba9 (Added Codex, working on upgrade, cancel, and reactivation flow)
    # ============================================================
    if etype == 'checkout.session.completed':
        session = obj
        metadata = session.get("metadata", {}) or {}

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
<<<<<<< HEAD
=======
        sub_id = sub.get('id')

        # Reactivation flip: promote pending → active
        if _subscription_has_reactivation_meta(sub_id):
            admin_id = (sub.get("metadata") or {}).get("admin_id")
            user = _user_from_admin_id(admin_id)
            if not user:
                try:
                    cust = stripe.Customer.retrieve(sub.get("customer"))
                    user = get_user_model().objects.filter(email=cust.get("email")).first()
                except Exception:
                    user = None
            if not user:
                return HttpResponse(status=200)

            active = Profile.objects.filter(user=user, is_active=True).first()
            pending = Profile.objects.filter(user=user, is_active=False).first()
            if pending and active:
                if pending.subscription_start is None:
                    pending.subscription_start = timezone.now()
                pending.is_active = True
                pending.save()
                if active.subscription_end is None:
                    active.subscription_end = timezone.now()
                active.is_active = False
                active.save()
                _log_admin_event(
                    user.email if user else None,
                    "plan_change_scheduled_applied",
                    f"subscription_id={sub_id}"
                )
            return HttpResponse(status=200)

        # ---------- General sync ----------
>>>>>>> f5fcba9 (Added Codex, working on upgrade, cancel, and reactivation flow)
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
        new_plan = None
        try:
            items = (sub.get("items") or {}).get("data") or []
            price_id = items[0].get("price", {}).get("id") if items else None
            new_plan = _plan_from_price_id(price_id)
        except Exception:
            new_plan = None

<<<<<<< HEAD
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

=======
        profile = Profile.objects.filter(user__email=email, is_active=True).order_by("-created_at").first() or \
                  Profile.objects.filter(user__email=email).order_by("-created_at").first()
        if not profile:
            return HttpResponse(status=200)

        # Guard: do not let stale trialing/canceled updates from old subscriptions
        # overwrite an already-active paid profile.
        if not profile.is_trial:
            if status_val == "trialing":
                return HttpResponse(status=200)
            if status_val == "canceled" and new_plan and profile.plan_id and new_plan.id != profile.plan_id:
                return HttpResponse(status=200)

        # Scheduled change applied (non-reactivation path): flip active profile to new plan.
        if status_val in ("active", "trialing") and new_plan and profile.plan_id != new_plan.id:
            user = profile.user
            old_profile = Profile.objects.filter(user=user, is_active=True).first()
            if old_profile:
                old_profile.is_active = False
                old_profile.subscription_end = timezone.now()
                old_profile.save()
            pending = Profile.objects.filter(user=user, is_active=False, plan=new_plan).order_by("-created_at").first()
            if pending:
                pending.is_active = True
                pending.subscription_start = pending.subscription_start or timezone.now()
                pending.subscription_end = None
                pending.next_billing = current_period_end
                pending.is_canceled = cancel_at_period_end
                pending.is_trial = (status_val == "trialing")
                pending.save()
                profile = pending
            else:
                profile = Profile.objects.create(
                    user=user,
                    plan=new_plan,
                    is_active=True,
                    is_trial=(status_val == "trialing"),
                    is_canceled=cancel_at_period_end,
                    subscription_start=timezone.now(),
                    subscription_end=None,
                    next_billing=current_period_end,
                )
            resolved_status = _subscription_status_from_plan_name(new_plan.name)
            if resolved_status:
                user.subscription_status = resolved_status
                user.save(update_fields=["subscription_status"])
            _log_admin_event(
                email,
                "plan_change_scheduled_applied",
                f"new_plan={new_plan.name} subscription_id={sub_id}"
            )

        # Mirror Stripe to DB (fields that exist on Profile)
>>>>>>> f5fcba9 (Added Codex, working on upgrade, cancel, and reactivation flow)
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