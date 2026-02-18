import stripe
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from users.admin_area.models import AdminIdentity
from users.admin_area.utils.log_EventTracker import log_EventTracker

stripe.api_key = settings.STRIPE_SECRET_KEY


def _customer_for_user_email(email: str):
    ident = AdminIdentity.objects.filter(admin_email=email).first()
    if ident:
        try:
            res = stripe.Customer.search(query=f"metadata['admin_id']:'{ident.adminID}'", limit=1)
            if res and res.data:
                return res.data[0]
        except Exception:
            pass
    return None


def _card_payload_from_payment_method(pm_obj, customer_id):
    if not isinstance(pm_obj, dict):
        return None
    card = pm_obj.get("card") or {}
    if not card:
        return None
    return {
        "has_payment_method": True,
        "customer_id": customer_id,
        "brand": card.get("brand"),
        "last4": card.get("last4"),
        "exp_month": card.get("exp_month"),
        "exp_year": card.get("exp_year"),
    }


def _card_payload_from_source(source_obj, customer_id):
    if not isinstance(source_obj, dict):
        return None
    if source_obj.get("object") != "card":
        return None
    return {
        "has_payment_method": True,
        "customer_id": customer_id,
        "brand": source_obj.get("brand"),
        "last4": source_obj.get("last4"),
        "exp_month": source_obj.get("exp_month"),
        "exp_year": source_obj.get("exp_year"),
    }


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_payment_method(request):
    user = request.user
    if getattr(user, "role", None) != "admin":
        return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

    customer = _customer_for_user_email(user.email)
    if not customer:
        return Response({"has_payment_method": False}, status=200)

    customer_id = customer.get("id")
    try:
        customer_obj = stripe.Customer.retrieve(customer_id, expand=["invoice_settings.default_payment_method"])
    except Exception:
        return Response({"has_payment_method": False}, status=200)

    # 1) Preferred: customer invoice default payment method
    pm = (customer_obj.get("invoice_settings") or {}).get("default_payment_method")
    payload = _card_payload_from_payment_method(pm, customer_id)
    if payload:
        return Response(payload, status=200)

    # 2) Legacy sources: customer default_source
    default_source = customer_obj.get("default_source")
    if default_source:
        try:
            source_obj = stripe.Customer.retrieve_source(customer_id, default_source)
            payload = _card_payload_from_source(source_obj, customer_id)
            if payload:
                return Response(payload, status=200)
        except Exception:
            pass

    # 3) Active/trialing subscription-level defaults
    try:
        subs = stripe.Subscription.list(customer=customer_id, status="all", limit=20)
        for sub in (subs.data or []):
            if sub.get("status") not in ("active", "trialing", "past_due"):
                continue

            sub_default_pm = sub.get("default_payment_method")
            if sub_default_pm:
                try:
                    pm_obj = stripe.PaymentMethod.retrieve(sub_default_pm)
                    payload = _card_payload_from_payment_method(pm_obj, customer_id)
                    if payload:
                        return Response(payload, status=200)
                except Exception:
                    pass

            sub_default_source = sub.get("default_source")
            if sub_default_source:
                try:
                    source_obj = stripe.Customer.retrieve_source(customer_id, sub_default_source)
                    payload = _card_payload_from_source(source_obj, customer_id)
                    if payload:
                        return Response(payload, status=200)
                except Exception:
                    pass
    except Exception:
        pass

    # 4) Last fallback: any card payment method attached to customer
    try:
        pms = stripe.PaymentMethod.list(customer=customer_id, type="card", limit=1)
        if pms and pms.data:
            payload = _card_payload_from_payment_method(pms.data[0], customer_id)
            if payload:
                return Response(payload, status=200)
    except Exception:
        pass

    return Response({"has_payment_method": False, "customer_id": customer_id}, status=200)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_payment_method_update_session(request):
    user = request.user
    if getattr(user, "role", None) != "admin":
        return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

    customer = _customer_for_user_email(user.email)
    if not customer:
        return Response({"error": "No Stripe customer found."}, status=status.HTTP_400_BAD_REQUEST)

    frontend_url = getattr(settings, "FRONTEND_URL", None) or "http://localhost:3000"
    try:
        session = stripe.billing_portal.Session.create(
            customer=customer.get("id"),
            return_url=f"{frontend_url}/admin_settings",
        )
    except Exception:
        return Response({"error": "Could not open billing portal."}, status=status.HTTP_400_BAD_REQUEST)

    log_EventTracker(
        admin_email=user.email,
        event_type="payment_method_update_started",
        details=f"customer_id={customer.get('id')}",
    )
    return Response({"url": session.url}, status=200)
