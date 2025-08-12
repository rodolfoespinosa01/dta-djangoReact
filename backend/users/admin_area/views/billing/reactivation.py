from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from users.admin_area.models import Plan, Profile

# ---- Helpers ---------------------------------------------------------------

def _period_from_name(name: str) -> str:
    if name == "adminMonthly":
        return "/mo"
    if name == "adminQuarterly":
        return "/qr"
    if name == "adminAnnual":
        return "/yr"
    return ""

# which paid plans can start with a trial on reactivation (business rule)
TRIAL_ALLOWED = {
    "adminMonthly": True,
    "adminQuarterly": True,
    "adminAnnual": False,
}

def _serialize_plans():
    """
    Return only PAID plans (exclude adminTrial) sorted by price.
    Fields used by FE:
      - price_id (Stripe Price ID)
      - display_name
      - price_display (e.g. $19.00/mo)
      - allow_trial (bool)
      - trial_days (int, optional)
    """
    rows = Plan.objects.all().order_by("price_cents", "name")
    out = []
    for p in rows:
        if p.name == "adminTrial":
            continue  # not purchasable in reactivation picker

        price_cents = getattr(p, "price_cents", None) or 0
        out.append({
            "id": p.id,
            "name": p.name,  # e.g., adminMonthly
            "display_name": getattr(p, "get_name_display", lambda: p.name)(),
            "price_id": p.stripe_price_id,
            "price_display": f"${price_cents/100:.2f}{_period_from_name(p.name)}",
            "allow_trial": TRIAL_ALLOWED.get(p.name, False),
            "trial_days": getattr(p, "trial_days", 7) if TRIAL_ALLOWED.get(p.name, False) else 0,
        })
    # keep exactly 3 plans visible (Monthly, Quarterly, Annual) if present
    # and ensure they’re in a stable order
    preferred = {"adminMonthly": 1, "adminQuarterly": 2, "adminAnnual": 3}
    out.sort(key=lambda x: preferred.get(x["name"], 99))
    return out

def _reactivation_mode(profile: Profile | None) -> str:
    """
    Decide the reactivation mode:
      - 'new_subscription' for canceled users, trial-expired, past_due, or explicit is_cancel flag
      - 'uncancel' for active but cancel_at_period_end users
      - 'none' otherwise
    """
    if profile is None:
        return "new_subscription"

    # Explicit “reactivate” flag you mentioned
    if getattr(profile, "is_cancel", False):
        return "new_subscription"

    # Scheduled cancel but still active → offer to uncancel
    if getattr(profile, "cancel_at_period_end", False):
        return "uncancel"

    status_val = (getattr(profile, "subscription_status", "") or "").lower()
    if status_val in {"canceled", "incomplete_expired", "past_due"}:
        return "new_subscription"

    return "none"

# ---- Endpoints -------------------------------------------------------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def preview(request):
    """
    FE uses this to decide what to show:
      {
        reactivation_mode: 'new_subscription' | 'uncancel' | 'none',
        plans: [ ...always include paid plans... ],
        plan_price_id: '<price_id>' | null
      }
    """
    user = request.user
    profile = Profile.objects.filter(user=user).first()

    mode = _reactivation_mode(profile)

    # Default selected price_id (optional)
    plan_price_id = None
    if profile:
        # If you store the user’s last/desired price, set it here
        plan_price_id = getattr(profile, "stripe_price_id", None)

    return Response({
        "reactivation_mode": mode,
        "plans": _serialize_plans(),
        "plan_price_id": plan_price_id,
    }, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def start(request):
    """
    Starts reactivation:
      - 'uncancel': flip cancel_at_period_end = False
      - 'new_subscription': requires target_price_id, optionally with_trial
      Returns:
        { action: 'checkout', url: '...' }  -> FE should redirect
        { action: 'uncancelled' }           -> FE shows success
        { action: 'provisioned' }           -> if you provision without checkout
        { action: 'none' }                  -> no-op
    """
    user = request.user
    profile = Profile.objects.filter(user=user).first()
    mode = _reactivation_mode(profile)

    if mode == "none":
        return Response({"action": "none"}, status=status.HTTP_200_OK)

    if mode == "uncancel":
        if profile and hasattr(profile, "cancel_at_period_end"):
            profile.cancel_at_period_end = False
            profile.save(update_fields=["cancel_at_period_end"])
        return Response({"action": "uncancelled"}, status=status.HTTP_200_OK)

    # mode == 'new_subscription'
    payload = request.data or {}
    target_price_id = payload.get("target_price_id")
    with_trial = bool(payload.get("with_trial"))

    if not target_price_id:
        plans = _serialize_plans()
        if not plans:
            return Response({"error": "No plans available to purchase."},
                            status=status.HTTP_400_BAD_REQUEST)
        target_price_id = plans[0]["price_id"]

    # Stripe config
    stripe_key = getattr(settings, "STRIPE_SECRET_KEY", None)
    frontend_base = getattr(settings, "FRONTEND_BASE_URL", "http://localhost:3000")
    success_url = f"{frontend_base}/admin_settings?reactivated=1"
    cancel_url = f"{frontend_base}/admin_reactivate?canceled=1"

    # If Stripe isn’t configured, let FE continue testing
    if not stripe_key:
        return Response({
            "action": "checkout",
            "url": f"{frontend_base}/fake-checkout?price_id={target_price_id}&trial={'1' if with_trial else '0'}",
        }, status=status.HTTP_200_OK)

    # Real Stripe flow
    try:
        import stripe
        stripe.api_key = stripe_key

        # Optional trial: your Stripe Prices must allow trials via subscription_data
        subscription_data = {}
        if with_trial:
            # You can also set trial via Stripe Price settings; this is a safe default
            # Adjust to your business rule (e.g., use plan-specific trial_days)
            selected = next((p for p in _serialize_plans() if p["price_id"] == target_price_id), None)
            trial_days = (selected or {}).get("trial_days", 0)
            if trial_days > 0:
                subscription_data["trial_period_days"] = trial_days

        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": target_price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            customer=(getattr(profile, "stripe_customer_id", None) or None),
            allow_promotion_codes=False,
            subscription_data=subscription_data or None,
        )
        return Response({"action": "checkout", "url": session.url}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": f"Stripe error: {e}"}, status=status.HTTP_502_BAD_GATEWAY)
