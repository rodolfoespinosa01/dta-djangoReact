import typing as t
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from users.admin_area.models import Profile, Plan
from users.admin_area.views.api_contract import error, ok, require_admin


def _plan_to_dict(p: Plan) -> dict:
    # Make FE happy regardless of your exact model fields
    display_name = dict(Plan.PLAN_CHOICES).get(p.name, p.name)
    price_display = getattr(p, "pretty_price", None)  # optional
    allow_trial = bool(getattr(p, "allow_trial", False))
    trial_days = int(getattr(p, "trial_days", 0) or 0)

    return {
        "price_id": p.stripe_price_id,
        "display_name": display_name,
        "price_display": price_display,
        "allow_trial": allow_trial,
        "trial_days": trial_days,
    }


def _resolve_mode_and_reason(profile: Profile) -> t.Tuple[str, str]:
    """
    Decide what the FE should show.
    - 'uncancel'          => user has an active sub but set cancel_at_period_end
    - 'new_subscription'  => user needs to pick a plan & go to checkout
    - 'none'              => nothing to do (active and not canceling)
    """
    subscription_active = bool(getattr(profile, "subscription_active", False))
    # Some codebases use is_c, others is_canceled—support both
    is_canceled_flag = bool(
        getattr(profile, "is_canceled", None)
        if hasattr(profile, "is_canceled")
        else getattr(profile, "is_c", False)
    )

    if subscription_active:
        if is_canceled_flag:
            return "uncancel", "scheduled_cancel"
        return "none", "active"

    # Not active → needs a new sub (could be fully canceled or trial expired)
    return "new_subscription", "canceled"


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def preview(request):
    """
    Returns FE contract:

    {
      "reactivation_mode": "uncancel"|"new_subscription"|"none",
      "reason": "canceled"|"trial_expired"|"scheduled_cancel"|"active",
      "current_price_id": "price_..." | null,
      "plans": [{ price_id, display_name, price_display, allow_trial, trial_days }, ...]
    }
    """
    user = request.user
    auth_error = require_admin(request)
    if auth_error:
        return auth_error

    try:
        profile = user.profiles.get(is_active=True)
    except Profile.DoesNotExist:
        return error(code="PROFILE_NOT_FOUND", message="Admin profile not found.", http_status=404)

    mode, reason = _resolve_mode_and_reason(profile)

    # Always return plans so FE can show grid in both 'new_subscription' and 'uncancel'
    plans_qs = Plan.objects.filter(
        name__in=["adminMonthly", "adminQuarterly", "adminAnnual"]
    ).exclude(stripe_price_id__isnull=True).exclude(stripe_price_id="")

    plans = [_plan_to_dict(p) for p in plans_qs]

    current_price_id = getattr(profile, "current_price_id", None)
    # Some codebases don’t store current_price_id; try deriving from Plan if present on Profile
    if not current_price_id and hasattr(profile, "plan") and getattr(profile.plan, "stripe_price_id", None):
        current_price_id = profile.plan.stripe_price_id

    return ok({
        "reactivation_mode": mode,
        "reason": reason,
        "current_price_id": current_price_id,
        "plans": plans,
    })
