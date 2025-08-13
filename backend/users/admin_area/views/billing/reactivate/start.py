import stripe
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from users.admin_area.models import Profile, AdminIdentity, Plan  # Plan optional if you want to validate price -> plan

stripe.api_key = getattr(settings, "STRIPE_SECRET_KEY", None)


def _candidate_email(user, profile):
    # Prefer user.email; fall back to AdminIdentity if needed
    email = getattr(user, "email", None)
    if email:
        return email
    try:
        ident = AdminIdentity.objects.get(admin_email=getattr(profile, "email", "") or "")
        return ident.admin_email
    except AdminIdentity.DoesNotExist:
        return None


def _admin_identity_for(user):
    # Ensure AdminIdentity exists and return (uuid_str, email)
    ident, _ = AdminIdentity.objects.get_or_create(admin_email=getattr(user, "email", ""))
    return str(ident.adminID), ident.admin_email


def _find_existing_customer_id(admin_id: str, email: str | None):
    # Prefer Customer Search by metadata(admin_id); fallback to listing by email
    try:
        res = stripe.Customer.search(query=f"metadata['admin_id']:'{admin_id}'", limit=1)
        if res and res.data:
            return res.data[0].id
    except Exception:
        pass
    if email:
        try:
            res = stripe.Customer.list(email=email, limit=1)
            if res and res.data:
                return res.data[0].id
        except Exception:
            pass
    return None


def _active_subscription_id_for_admin_id(admin_id: str) -> str | None:
    # Find the active sub for the Customer tagged with this admin_id
    try:
        custs = stripe.Customer.search(query=f"metadata['admin_id']:'{admin_id}'", limit=1)
        if custs and custs.data:
            subs = stripe.Subscription.list(customer=custs.data[0].id, status="active", limit=1)
            if subs and subs.data:
                return subs.data[0].id
    except Exception:
        pass
    return None


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def start(request):
    """
    POST body:

    1) Uncancel current plan:
       {}  -> { "action": "uncancelled" }

    2) Reactivate/Upgrade via Checkout:
       { "target_price_id": "price_xxx", "with_trial": bool }
       -> { "action": "checkout", "url": "https://checkout.stripe.com/..." }
    """
    user = request.user
    if getattr(user, "role", None) != "admin":
        return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

    # Your invariant expects exactly one active Profile; if none, bail (UI should guide)
    try:
        profile = user.profiles.get(is_active=True)
    except Profile.DoesNotExist:
        return Response({"error": "Admin profile not found."}, status=status.HTTP_404_NOT_FOUND)

    payload = request.data or {}
    target_price_id = payload.get("target_price_id")
    with_trial = bool(payload.get("with_trial", False))

    # Prepare identity + email (used for both paths)
    admin_id, admin_email = _admin_identity_for(user)
    email = _candidate_email(user, profile) or admin_email

    frontend_url = getattr(settings, "FRONTEND_URL", None) or "http://localhost:3000"
    success_url = f"{frontend_url}/admin_dashboard?status=success&src=reactivation"
    cancel_url = f"{frontend_url}/admin_billing?status=cancel&src=reactivation"

    # ---------------- UNCANCEL (no Checkout) ----------------
    if not target_price_id:
        # Find the current Stripe subscription (by admin_id) and flip cancel_at_period_end off
        current_sub_id = _active_subscription_id_for_admin_id(admin_id)
        if not current_sub_id:
            return Response({"error": "No active Stripe subscription found to uncancel."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            stripe.Subscription.modify(current_sub_id, cancel_at_period_end=False)
        except Exception:
            return Response({"error": "Could not uncancel on Stripe."}, status=status.HTTP_400_BAD_REQUEST)

        # Mirror locally
        profile.is_canceled = False
        profile.save(update_fields=["is_canceled"])
        return Response({"action": "uncancelled"})

    # ---------------- CHECKOUT (reactivate/upgrade) ----------------
    # Optionally validate the price belongs to a known Plan (nice safety, can be removed)
    try:
        _ = Plan.objects.get(stripe_price_id=target_price_id)
    except Exception:
        pass  # skip if you don't want to enforce

    # Reuse existing Customer if possible; otherwise let Checkout create (via email)
    customer_id = _find_existing_customer_id(admin_id, email)

    subscription_data = {
        "metadata": {
            "reactivation": "1",
            "admin_id": admin_id,
            "admin_email": email or "",
            "admin_user_id": str(getattr(user, "id", "")),
        }
    }
    if with_trial:
        subscription_data["trial_period_days"] = 7  # backend decides; FE only requested

    session_kwargs = dict(
        mode="subscription",
        line_items=[{"price": target_price_id, "quantity": 1}],
        allow_promotion_codes=True,
        subscription_data=subscription_data,
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={  # session-level too
            "reactivation": "1",
            "admin_id": admin_id,
            "admin_email": email or "",
            "admin_user_id": str(getattr(user, "id", "")),
        },
    )

    if customer_id:
        session_kwargs["customer"] = customer_id
    else:
        # Let Checkout create customer, tie to email
        if email:
            session_kwargs["customer_creation"] = "always"
            session_kwargs["customer_email"] = email

    try:
        session = stripe.checkout.Session.create(**session_kwargs)
    except Exception:
        return Response({"error": "Could not create checkout session."}, status=status.HTTP_400_BAD_REQUEST)

    return Response({"action": "checkout", "url": session.url})
