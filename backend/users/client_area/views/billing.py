from datetime import timedelta

import stripe
from django.conf import settings
from django.http import HttpResponse
from django.utils.crypto import get_random_string
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated

from users.admin_area.models import AdminIdentity
from users.client_area.models import ClientPendingSignup, ClientProfile, ClientQueuedPlanChange
from users.client_area.services.pricing import (
    COACHING_ADDON_CENTS,
    OFFER_CATALOG,
    PAID_OFFER_CODES,
    QuoteError,
    build_client_purchase_quote,
)
from users.client_area.views.api_contract import error, ok, require_client
from users.client_area.views.auth_flow import (
    _apply_coaching_to_profile,
    _apply_offer_to_profile,
    _build_client_settings_payload,
)

stripe.api_key = getattr(settings, "STRIPE_SECRET_KEY", None)
CLIENT_ENDPOINT_SECRET = getattr(settings, "STRIPE_WEBHOOK_SECRET", None)
FRONTEND_URL = getattr(settings, "FRONTEND_URL", None) or "https://localhost:3000"

def _coaching_label(coaching_term: str) -> str:
    return {
        "none": "No Coaching",
        "1_month": "Coaching Add-On (1 Month)",
        "3_months": "Coaching Add-On (3 Months)",
    }.get(coaching_term, "Coaching Add-On")


def _stripe_once_discount_from_quote(quote):
    discount = (quote or {}).get("discount") or {}
    amounts = (quote or {}).get("amounts") or {}
    discount_cents = int(amounts.get("discount_cents") or 0)
    if not discount or discount_cents <= 0:
        return None

    coupon_kwargs = {
        "duration": "once",
        "name": f"App Discount {discount.get('code') or ''}".strip(),
        "metadata": {
            "source": "app_discount_code",
            "code": str(discount.get("code") or ""),
        },
    }
    if str(discount.get("discount_type") or "") == "percent" and discount.get("percent_off") is not None:
        coupon_kwargs["percent_off"] = float(discount.get("percent_off"))
    else:
        coupon_kwargs["amount_off"] = discount_cents
        coupon_kwargs["currency"] = "usd"

    coupon = stripe.Coupon.create(**coupon_kwargs)
    return {"coupon": coupon.id}


def _validate_checkout_choice(offer_code: str, coaching_term: str):
    if offer_code not in PAID_OFFER_CODES:
        return "INVALID_OFFER"
    # Client checkout now uses fixed plan variants (monthly / monthly+coaching).
    if coaching_term != "none":
        return "INVALID_COACHING_TERM"
    if coaching_term not in COACHING_ADDON_CENTS:
        return "INVALID_COACHING_TERM"
    return None


def _quote_error_response(exc: QuoteError):
    return error(exc.code, exc.message, http_status=400)


def _build_client_quote(profile: ClientProfile, *, email: str, offer_code: str, coaching_term: str, discount_code: str, purchase_mode: str):
    return build_client_purchase_quote(
        email=email,
        offer_code=offer_code,
        coaching_term=coaching_term,
        sale_channel=profile.sale_channel,
        purchase_mode=purchase_mode,
        associated_admin_id=profile.associated_admin_id,
        discount_code=discount_code,
        trial_eligible=profile.offer_code == "macro_calculator_free" and purchase_mode == "subscription",
    )


def _apply_client_checkout_upgrade(profile: ClientProfile, *, offer_code: str, coaching_term: str, stripe_customer_id: str = "", stripe_subscription_id: str = ""):
    if offer_code not in PAID_OFFER_CODES:
        return profile
    use_trial = profile.offer_code == "macro_calculator_free"
    _apply_offer_to_profile(profile, offer_code, use_trial_if_eligible=use_trial)
    offer = OFFER_CATALOG.get(offer_code) or {}
    if offer.get("includes_coaching"):
        profile.includes_coaching = True
        profile.coaching_expires_at = None
        profile.save(update_fields=["includes_coaching", "coaching_expires_at", "updated_at"])
    else:
        _apply_coaching_to_profile(profile, coaching_term if coaching_term in COACHING_ADDON_CENTS else "none")
    if stripe_customer_id:
        profile.stripe_customer_id = stripe_customer_id
    if stripe_subscription_id:
        profile.stripe_subscription_id = stripe_subscription_id
    profile.is_active = True
    profile.cancel_at_period_end = False
    profile.save(update_fields=["stripe_customer_id", "stripe_subscription_id", "is_active", "cancel_at_period_end", "updated_at"])
    return profile


def _get_current_period_end(profile: ClientProfile):
    if not stripe.api_key or not profile.stripe_subscription_id:
        return None
    try:
        sub = stripe.Subscription.retrieve(profile.stripe_subscription_id)
        ts = sub.get("current_period_end")
        if ts:
            return timezone.datetime.fromtimestamp(int(ts), tz=timezone.utc)
    except Exception:
        return None
    return None


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def client_checkout_quote(request):
    auth_error = require_client(request)
    if auth_error:
        return auth_error

    profile = ClientProfile.objects.filter(user=request.user).select_related("associated_admin").first()
    if not profile:
        return error("CLIENT_PROFILE_NOT_FOUND", "Client profile not found.", http_status=404)

    payload = request.data or {}
    offer_code = str(payload.get("offer_code") or "").strip()
    coaching_term = str(payload.get("coaching_term") or "none").strip()
    discount_code = str(payload.get("discount_code") or "").strip()
    purchase_mode = str(payload.get("purchase_mode") or "subscription").strip().lower()

    try:
        quote = _build_client_quote(
            profile,
            email=request.user.email,
            offer_code=offer_code,
            coaching_term=coaching_term,
            discount_code=discount_code,
            purchase_mode=purchase_mode,
        )
    except QuoteError as exc:
        return _quote_error_response(exc)

    return ok({"quote": quote})


@api_view(["GET"])
@permission_classes([AllowAny])
def client_signup_checkout_debug_link(request):
    if not getattr(settings, "DEBUG", False):
        return error("FORBIDDEN", "This endpoint is available only in DEBUG mode.", http_status=403)

    session_id = str(request.GET.get("session_id") or "").strip()
    if not session_id:
        return error("MISSING_SESSION_ID", "session_id is required.", http_status=400)

    pending = ClientPendingSignup.objects.filter(stripe_checkout_session_id=session_id).first()
    if not pending:
        return ok({"status": "pending"})

    if not (pending.registration_link or "").strip():
        return ok({"status": "pending"})

    return ok(
        {
            "status": "ready",
            "debug_registration_link": pending.registration_link,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def client_start_checkout_session(request):
    auth_error = require_client(request)
    if auth_error:
        return auth_error

    if not stripe.api_key:
        return error("STRIPE_NOT_CONFIGURED", "Stripe is not configured on the server.", http_status=500)

    profile = ClientProfile.objects.filter(user=request.user).select_related("associated_admin").first()
    if not profile:
        return error("CLIENT_PROFILE_NOT_FOUND", "Client profile not found.", http_status=404)

    payload = request.data or {}
    offer_code = str(payload.get("offer_code") or "").strip()
    coaching_term = str(payload.get("coaching_term") or "none").strip()
    discount_code = str(payload.get("discount_code") or "").strip()
    validation_error = _validate_checkout_choice(offer_code, coaching_term)
    if validation_error == "INVALID_OFFER":
        return error("INVALID_OFFER", "Select a valid paid plan.", http_status=400)
    if validation_error == "INVALID_COACHING_TERM":
        return error("INVALID_COACHING_TERM", "Choose a monthly plan variant. Coaching is included only in the coaching plan.", http_status=400)

    try:
        quote = _build_client_quote(
            profile,
            email=request.user.email,
            offer_code=offer_code,
            coaching_term=coaching_term,
            discount_code=discount_code,
            purchase_mode="subscription",
        )
    except QuoteError as exc:
        return _quote_error_response(exc)

    offer = OFFER_CATALOG[offer_code]
    trial_days = int(quote["trial_days"])
    if int((quote.get("amounts") or {}).get("total_cents") or 0) <= 0:
        return error(
            "UNSUPPORTED_ZERO_AMOUNT_SUBSCRIPTION",
            "This discount reduces the first checkout charge to $0.00, which is not supported in the current checkout flow.",
            http_status=400,
        )

    # Find or create Stripe customer for this client
    customer = None
    if profile.stripe_customer_id:
      try:
          customer = stripe.Customer.retrieve(profile.stripe_customer_id)
      except Exception:
          customer = None
    if not customer:
        customer = stripe.Customer.create(
            email=request.user.email,
            metadata={
                "client_user_id": str(request.user.id),
                "sale_channel": profile.sale_channel,
                "associated_admin_id": str(profile.associated_admin_id or ""),
            },
        )
        profile.stripe_customer_id = customer.id
        profile.save(update_fields=["stripe_customer_id", "updated_at"])

    stripe_discount = _stripe_once_discount_from_quote(quote)
    allow_promotion_codes = not bool(stripe_discount)
    stripe_price_id = str(offer.get("stripe_price_id") or "").strip()
    if not stripe_price_id:
        return error("STRIPE_PRICE_NOT_CONFIGURED", "Stripe price is not configured for this plan.", http_status=500)

    line_items = [{"price": stripe_price_id, "quantity": 1}]
    coaching_line_amount = int((quote.get("amounts") or {}).get("coaching_addon_final_cents") or 0)
    if coaching_term != "none" and coaching_line_amount > 0:
        line_items.append(
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": _coaching_label(coaching_term)},
                    "unit_amount": coaching_line_amount,
                },
                "quantity": 1,
            }
        )

    subscription_data = {
        "metadata": {
            "flow": "client_upgrade_checkout",
            "client_user_id": str(request.user.id),
            "client_profile_id": str(profile.id),
            "offer_code": offer_code,
            "coaching_term": coaching_term,
            "sale_channel": profile.sale_channel,
            "associated_admin_id": str(profile.associated_admin_id or ""),
            "discount_code": (quote.get("discount") or {}).get("code", ""),
            "discount_cents": str((quote.get("amounts") or {}).get("discount_cents") or 0),
        }
    }
    if trial_days > 0:
        subscription_data["trial_period_days"] = int(trial_days)

    session_kwargs = dict(
        mode="subscription",
        payment_method_types=["card"],
        customer=customer.id,
        allow_promotion_codes=allow_promotion_codes,
        line_items=line_items,
        subscription_data=subscription_data,
        metadata={
            "flow": "client_upgrade_checkout",
            "client_user_id": str(request.user.id),
            "client_profile_id": str(profile.id),
            "offer_code": offer_code,
            "coaching_term": coaching_term,
            "discount_code": (quote.get("discount") or {}).get("code", ""),
        },
        success_url=f"{FRONTEND_URL}/client_settings?checkout=success&session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{FRONTEND_URL}/client_settings?checkout=cancel",
    )
    if stripe_discount:
        session_kwargs["discounts"] = [stripe_discount]

    session = stripe.checkout.Session.create(**session_kwargs)

    return ok(
        {
            "checkout_url": session.url,
            "checkout_session_id": session.id,
            "trial_days": trial_days,
            "offer_code": offer_code,
            "coaching_term": coaching_term,
            "quote": quote,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def client_checkout_sync(request):
    auth_error = require_client(request)
    if auth_error:
        return auth_error
    if not stripe.api_key:
        return error("STRIPE_NOT_CONFIGURED", "Stripe is not configured on the server.", http_status=500)

    profile = ClientProfile.objects.filter(user=request.user).select_related("associated_admin").first()
    if not profile:
        return error("CLIENT_PROFILE_NOT_FOUND", "Client profile not found.", http_status=404)

    session_id = str((request.data or {}).get("session_id") or "").strip()
    if not session_id:
        return error("MISSING_SESSION_ID", "Missing Stripe checkout session id.", http_status=400)
    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except Exception as exc:
        return error("STRIPE_SESSION_LOOKUP_FAILED", f"Could not load checkout session: {exc}", http_status=400)

    metadata = session.get("metadata", {}) or {}
    flow = metadata.get("flow")
    if flow not in {"client_upgrade_checkout", "client_queue_plan_change_checkout"}:
        return error("INVALID_SESSION_FLOW", "Checkout session does not belong to client upgrade flow.", http_status=400)

    if str(metadata.get("client_user_id") or "") != str(request.user.id):
        return error("FORBIDDEN", "Checkout session does not belong to this client.", http_status=403)

    payment_status = str(session.get("payment_status") or "")
    checkout_status = str(session.get("status") or "")
    if checkout_status != "complete":
        return ok(
            {
                "message": "Checkout not completed yet.",
                "checkout": {"status": checkout_status, "payment_status": payment_status},
                "settings": _build_client_settings_payload(profile),
            }
        )

    offer_code = str(metadata.get("offer_code") or "").strip()
    coaching_term = str(metadata.get("coaching_term") or "none").strip()
    if flow == "client_upgrade_checkout":
        _apply_client_checkout_upgrade(
            profile,
            offer_code=offer_code,
            coaching_term=coaching_term,
            stripe_customer_id=str(session.get("customer") or ""),
            stripe_subscription_id=str(session.get("subscription") or ""),
        )
    elif flow == "client_queue_plan_change_checkout":
        session_id_value = str(session.get("id") or "")
        if session_id_value and not ClientQueuedPlanChange.objects.filter(stripe_checkout_session_id=session_id_value).exists():
            q_ts = str(metadata.get("queued_for_period_end_at") or "").strip()
            queued_for = None
            if q_ts:
                try:
                    queued_for = timezone.datetime.fromisoformat(q_ts)
                except Exception:
                    queued_for = None
            ClientQueuedPlanChange.objects.create(
                user=profile.user,
                client_profile=profile,
                target_offer_code=offer_code,
                target_coaching_term=coaching_term,
                amount_cents=int(session.get("amount_total") or 0),
                queued_for_period_end_at=queued_for,
                stripe_checkout_session_id=session_id_value,
                stripe_payment_intent_id=str(session.get("payment_intent") or ""),
                status="queued",
                notes="Queued prepaid change (no proration).",
            )
    return ok(
        {
            "message": "Checkout synced successfully.",
            "checkout": {"status": checkout_status, "payment_status": payment_status},
            "settings": _build_client_settings_payload(profile),
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def client_start_queued_checkout_session(request):
    auth_error = require_client(request)
    if auth_error:
        return auth_error
    if not stripe.api_key:
        return error("STRIPE_NOT_CONFIGURED", "Stripe is not configured on the server.", http_status=500)

    profile = ClientProfile.objects.filter(user=request.user).select_related("associated_admin").first()
    if not profile:
        return error("CLIENT_PROFILE_NOT_FOUND", "Client profile not found.", http_status=404)
    if not (profile.is_active and profile.includes_food_plan and profile.offer_code in PAID_OFFER_CODES):
        return error("ACTIVE_PAID_PLAN_REQUIRED", "Queued plan changes require an active paid food plan.", http_status=400)

    payload = request.data or {}
    offer_code = str(payload.get("offer_code") or "").strip()
    coaching_term = str(payload.get("coaching_term") or "none").strip()
    discount_code = str(payload.get("discount_code") or "").strip()
    validation_error = _validate_checkout_choice(offer_code, coaching_term)
    if validation_error == "INVALID_OFFER":
        return error("INVALID_OFFER", "Select a valid paid plan.", http_status=400)
    if validation_error == "INVALID_COACHING_TERM":
        return error("INVALID_COACHING_TERM", "Choose a monthly plan variant. Coaching is included only in the coaching plan.", http_status=400)

    offer = OFFER_CATALOG[offer_code]
    try:
        quote = _build_client_quote(
            profile,
            email=request.user.email,
            offer_code=offer_code,
            coaching_term=coaching_term,
            discount_code=discount_code,
            purchase_mode="payment",
        )
    except QuoteError as exc:
        return _quote_error_response(exc)

    plan_line_amount = int((quote.get("amounts") or {}).get("plan_final_cents") or 0)
    coaching_amount = int((quote.get("amounts") or {}).get("coaching_addon_final_cents") or 0)
    total_amount = int((quote.get("amounts") or {}).get("total_cents") or 0)
    if total_amount <= 0:
        return error(
            "UNSUPPORTED_ZERO_AMOUNT_CHECKOUT",
            "This discount reduces the checkout total to $0.00, which is not supported in the current checkout flow.",
            http_status=400,
        )
    queued_for = _get_current_period_end(profile)

    customer = None
    if profile.stripe_customer_id:
        try:
            customer = stripe.Customer.retrieve(profile.stripe_customer_id)
        except Exception:
            customer = None
    if not customer:
        customer = stripe.Customer.create(email=request.user.email, metadata={"client_user_id": str(request.user.id)})
        profile.stripe_customer_id = customer.id
        profile.save(update_fields=["stripe_customer_id", "updated_at"])

    line_items = []
    if plan_line_amount > 0:
        line_items.append(
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": f"Queued Plan Change: {'Weekly' if offer.get('billing_cycle') == 'weekly' else 'Monthly'} (No Proration)"},
                    "unit_amount": plan_line_amount,
                },
                "quantity": 1,
            }
        )
    if coaching_term != "none" and coaching_amount > 0:
        line_items.append(
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": f"Queued {_coaching_label(coaching_term)}"},
                    "unit_amount": int(coaching_amount),
                },
                "quantity": 1,
            }
        )
    if not line_items:
        return error("INVALID_CHECKOUT_TOTAL", "No payable line items were generated for checkout.", http_status=400)

    session = stripe.checkout.Session.create(
        mode="payment",
        payment_method_types=["card"],
        customer=customer.id,
        allow_promotion_codes=True,
        line_items=line_items,
        metadata={
                "flow": "client_queue_plan_change_checkout",
                "client_user_id": str(request.user.id),
                "client_profile_id": str(profile.id),
                "offer_code": offer_code,
                "coaching_term": coaching_term,
                "discount_code": (quote.get("discount") or {}).get("code", ""),
                "discount_cents": str((quote.get("amounts") or {}).get("discount_cents") or 0),
                "queued_for_period_end_at": queued_for.isoformat() if queued_for else "",
            },
        success_url=f"{FRONTEND_URL}/client_settings?queued_checkout=success&session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{FRONTEND_URL}/client_settings?queued_checkout=cancel",
    )

    return ok(
        {
            "checkout_url": session.url,
            "checkout_session_id": session.id,
            "amount_cents": total_amount,
            "queued_for_period_end_at": queued_for,
            "quote": quote,
        }
    )


@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def client_stripe_webhook(request):
    if not stripe.api_key or not CLIENT_ENDPOINT_SECRET:
        return HttpResponse(status=200)

    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, CLIENT_ENDPOINT_SECRET)
    except Exception:
        return HttpResponse(status=400)

    etype = event.get("type")
    obj = event["data"]["object"]

    if etype == "checkout.session.completed":
        session = obj
        metadata = session.get("metadata", {}) or {}
        flow = metadata.get("flow")
        if flow == "public_client_signup_checkout":
            email = str(metadata.get("signup_email") or "").strip().lower()
            offer_code = str(metadata.get("offer_code") or "").strip()
            sale_channel = str(metadata.get("sale_channel") or "dta_direct").strip() or "dta_direct"
            admin_slug = str(metadata.get("admin_slug") or "").strip().lower()
            if not email or not offer_code:
                return HttpResponse(status=200)
            if offer_code not in OFFER_CATALOG:
                return HttpResponse(status=200)

            admin = None
            if admin_slug:
                admin = AdminIdentity.objects.filter(subdomain_slug=admin_slug).first()

            # Prevent duplicate pending rows from repeated webhook deliveries.
            existing_pending = ClientPendingSignup.objects.filter(
                email__iexact=email,
                status=ClientPendingSignup.STATUS_PENDING,
            ).first()
            if existing_pending:
                existing_pending.status = ClientPendingSignup.STATUS_SUPERSEDED
                existing_pending.save(update_fields=["status"])

            offer = OFFER_CATALOG[offer_code]
            try:
                trial_days = int(metadata.get("trial_days") or 0)
            except (TypeError, ValueError):
                trial_days = 0
            try:
                amount_cents = int(metadata.get("amount_cents") or offer.get("amount_cents") or 0)
            except (TypeError, ValueError):
                amount_cents = int(offer.get("amount_cents") or 0)

            includes_food_plan = str(metadata.get("includes_food_plan") or ("1" if offer.get("includes_food_plan") else "0")) in {"1", "true", "True"}
            includes_coaching = str(metadata.get("includes_coaching") or ("1" if offer.get("includes_coaching") else "0")) in {"1", "true", "True"}

            token = get_random_string(64)
            registration_link = f"{FRONTEND_URL}/client_register?token={token}"
            pending = ClientPendingSignup.objects.create(
                email=email,
                token=token,
                admin=admin,
                sale_channel=sale_channel,
                offer_code=offer_code,
                billing_cycle=offer["billing_cycle"],
                trial_days=max(0, trial_days),
                amount_cents=max(0, amount_cents),
                includes_food_plan=includes_food_plan,
                includes_coaching=includes_coaching,
                registration_link=registration_link,
                status=ClientPendingSignup.STATUS_PENDING,
                stripe_checkout_session_id=str(session.get("id") or ""),
                registration_link_printed_at=timezone.now(),
            )

            print("\n" + "=" * 60)
            print("📩 Client registration email (simulated after Stripe checkout):")
            print(f"To: {email}")
            print("Subject: Finish setting up your DTA account")
            print(f"➡️ Click to register:\n{registration_link}")
            print("=" * 60 + "\n")
            return HttpResponse(status=200)

        if flow == "client_queue_plan_change_checkout":
            try:
                user_id = int(metadata.get("client_user_id") or 0)
            except (TypeError, ValueError):
                return HttpResponse(status=200)
            profile = ClientProfile.objects.filter(user_id=user_id).first()
            if not profile:
                return HttpResponse(status=200)
            session_id = str(session.get("id") or "")
            if session_id and ClientQueuedPlanChange.objects.filter(stripe_checkout_session_id=session_id).exists():
                return HttpResponse(status=200)
            q_ts = str(metadata.get("queued_for_period_end_at") or "").strip()
            queued_for = None
            if q_ts:
                try:
                    queued_for = timezone.datetime.fromisoformat(q_ts)
                except Exception:
                    queued_for = None
            line_total = int(session.get("amount_total") or 0)
            ClientQueuedPlanChange.objects.create(
                user=profile.user,
                client_profile=profile,
                target_offer_code=str(metadata.get("offer_code") or ""),
                target_coaching_term=str(metadata.get("coaching_term") or "none"),
                amount_cents=line_total,
                queued_for_period_end_at=queued_for,
                stripe_checkout_session_id=session_id,
                stripe_payment_intent_id=str(session.get("payment_intent") or ""),
                status="queued",
                notes="Queued prepaid change (no proration).",
            )
            return HttpResponse(status=200)

        if flow != "client_upgrade_checkout":
            return HttpResponse(status=200)

        try:
            user_id = int(metadata.get("client_user_id") or 0)
        except (TypeError, ValueError):
            return HttpResponse(status=200)
        offer_code = str(metadata.get("offer_code") or "").strip()
        coaching_term = str(metadata.get("coaching_term") or "none").strip()
        if offer_code not in PAID_OFFER_CODES:
            return HttpResponse(status=200)

        profile = ClientProfile.objects.filter(user_id=user_id).first()
        if not profile:
            return HttpResponse(status=200)

        incoming_sub_id = str(session.get("subscription") or "")
        if incoming_sub_id and profile.stripe_subscription_id == incoming_sub_id and profile.offer_code == offer_code and profile.coaching_term == coaching_term:
            return HttpResponse(status=200)

        _apply_client_checkout_upgrade(
            profile,
            offer_code=offer_code,
            coaching_term=coaching_term,
            stripe_customer_id=str(session.get("customer") or ""),
            stripe_subscription_id=incoming_sub_id,
        )
        return HttpResponse(status=200)

    if etype == "invoice.paid":
        invoice = obj
        customer_id = str(invoice.get("customer") or "")
        sub_id = str(invoice.get("subscription") or "")
        if not customer_id:
            return HttpResponse(status=200)
        profile = ClientProfile.objects.filter(stripe_customer_id=customer_id).first()
        if not profile:
            return HttpResponse(status=200)
        profile.is_active = True
        if sub_id:
            profile.stripe_subscription_id = sub_id
        profile.save(update_fields=["is_active", "stripe_subscription_id", "updated_at"])
        return HttpResponse(status=200)

    if etype == "customer.subscription.updated":
        sub = obj
        customer_id = str(sub.get("customer") or "")
        profile = ClientProfile.objects.filter(stripe_customer_id=customer_id).first()
        if not profile:
            return HttpResponse(status=200)
        status_val = str(sub.get("status") or "")
        profile.stripe_subscription_id = str(sub.get("id") or profile.stripe_subscription_id or "")
        profile.cancel_at_period_end = bool(sub.get("cancel_at_period_end"))
        profile.is_active = status_val in ("active", "trialing", "past_due")
        profile.save(update_fields=["stripe_subscription_id", "cancel_at_period_end", "is_active", "updated_at"])
        return HttpResponse(status=200)

    if etype == "customer.subscription.deleted":
        sub = obj
        customer_id = str(sub.get("customer") or "")
        profile = ClientProfile.objects.filter(stripe_customer_id=customer_id).first()
        if not profile:
            return HttpResponse(status=200)
        profile.cancel_at_period_end = False
        profile.is_active = False
        profile.save(update_fields=["cancel_at_period_end", "is_active", "updated_at"])
        return HttpResponse(status=200)

    return HttpResponse(status=200)
