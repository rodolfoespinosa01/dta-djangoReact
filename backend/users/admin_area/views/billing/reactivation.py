from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings

from users.admin_area.models import Plan, Profile

def _serialize_plans():
    qs = Plan.objects.all().order_by('price_cents')  # no .filter(active=True)
    return [
        {
            "id": p.id,
            "name": p.name,
            "display_name": p.name,
            "price_id": p.stripe_price_id,
            "price_display": f"${(p.price_cents or 0)/100:.2f}/mo",
        }
        for p in qs if p.stripe_price_id
    ]

def _reactivation_mode(profile: Profile | None):
    """
    Decide the reactivation mode based on the profile we have.
    Adjust the field names if yours differ.
    """
    if profile is None:
        return "new_subscription"

    # If user has a sub but set to end at period end -> allow uncancel
    if getattr(profile, "cancel_at_period_end", False):
        return "uncancel"

    status_val = getattr(profile, "subscription_status", "") or ""
    if status_val in ("canceled", "incomplete_expired", "past_due"):
        return "new_subscription"

    # Otherwise nothing to do
    return "none"

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def preview(request):
    user = request.user

    # (Optional) decide the mode from your profile/subscription
    # For now, keep it simple so FE can test:
    # - If user is canceled -> 'new_subscription'
    # - If uncancel available -> 'uncancel'
    # - Else 'none'
    try:
        from users.admin_area.models import Profile
        profile = Profile.objects.get(user=user)
        if getattr(profile, "cancel_at_period_end", False):
            mode = "uncancel"
        elif getattr(profile, "subscription_status", "") in ("canceled", "incomplete_expired", "past_due"):
            mode = "new_subscription"
        else:
            mode = "none"
        plan_price_id = getattr(profile, "stripe_price_id", None)
    except Exception:
        mode = "new_subscription"
        plan_price_id = None

    return Response({
        "reactivation_mode": mode,
        "plans": _serialize_plans(),     # 👈 always included
        "plan_price_id": plan_price_id,  # default selection if you have one
    }, status=status.HTTP_200_OK)



def _period_from_name(name: str) -> str:
    # suffix for price_display
    if name == "adminMonthly":
        return "/mo"
    if name == "adminQuarterly":
        return "/qr"
    if name == "adminAnnual":
        return "/yr"
    return ""  # adminTrial or unknown

def _serialize_plans():
    rows = Plan.objects.all().order_by("price_cents")
    out = []
    for p in rows:
        # skip trial for reactivation purchase flow
        if p.name == "adminTrial":
            continue
        out.append({
            "id": p.id,
            "name": p.name,  # e.g. adminMonthly
            "display_name": p.get_name_display(),  # "Monthly Admin Plan"
            "price_id": p.stripe_price_id,  # what Stripe Checkout needs
            "price_display": f"${(p.price_cents or 0)/100:.2f}{_period_from_name(p.name)}",
        })
    return out

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start(request):
    """
    Minimal, safe handler so URL import works and the flow unblocks.
    - If mode == 'uncancel': flip cancel_at_period_end=False (if the field exists).
    - If mode == 'new_subscription': require target_price_id and (optionally) return a checkout URL.
    - Else: return no-op.
    """
    user = request.user
    try:
        profile = Profile.objects.get(user=user)
    except Profile.DoesNotExist:
        profile = None

    mode = _reactivation_mode(profile)

    if mode == "none":
        return Response({"action": "none", "status": "noop"}, status=status.HTTP_200_OK)

    if mode == "uncancel":
        # Only flip the flag if the field exists
        if profile and hasattr(profile, "cancel_at_period_end"):
            setattr(profile, "cancel_at_period_end", False)
            profile.save(update_fields=["cancel_at_period_end"])
        return Response({"action": "none", "status": "uncanceled"}, status=status.HTTP_200_OK)

    # mode == "new_subscription"
    payload = request.data or {}
    target_price_id = payload.get("target_price_id")

    if not target_price_id:
        # Try to default to first available plan
        plans = _serialize_plans()
        if plans:
            target_price_id = plans[0]["price_id"]
        else:
            return Response({"error": "No plans available to purchase."},
                            status=status.HTTP_400_BAD_REQUEST)

    # If you already have Stripe wired, you can create a Checkout Session here.
    # To keep this import-safe for makemigrations, we guard on presence of key.
    stripe_key = getattr(settings, "STRIPE_SECRET_KEY", None)
    frontend_base = getattr(settings, "FRONTEND_BASE_URL", "http://localhost:3000")
    success_url = f"{frontend_base}/admin_settings?reactivated=1"
    cancel_url = f"{frontend_base}/admin_reactivate?canceled=1"

    if not stripe_key:
        # Dev-safe fallback so your frontend can still navigate
        return Response({
            "action": "checkout",
            "url": f"{frontend_base}/fake-checkout?price_id={target_price_id}",
        }, status=status.HTTP_200_OK)

    # Real Stripe flow (optional; remove guard above if you want to enforce keys)
    try:
        import stripe
        stripe.api_key = stripe_key

        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": target_price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            customer=getattr(profile, "stripe_customer_id", None) or None,
            allow_promotion_codes=False,
        )
        return Response({"action": "checkout", "url": session.url}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": f"Stripe error: {e}"}, status=status.HTTP_502_BAD_GATEWAY)
