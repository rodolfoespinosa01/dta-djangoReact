from rest_framework.decorators import api_view
from django.contrib.auth import get_user_model

from users.admin_area.models import AdminIdentity
from users.client_area.models import ClientProfile
from users.client_area.services.pricing import OFFER_CATALOG

TRIAL_ADMIN_CLIENT_LIMIT = 5


def _ok(payload, status=200):
    from rest_framework.response import Response
    return Response({"ok": True, **payload}, status=status)


def _error(code, message, status=400):
    from rest_framework.response import Response
    return Response(
        {"ok": False, "error": {"code": code, "message": message}, "error_code": code},
        status=status,
    )


def _display_name_from_identity(identity):
    slug = (identity.subdomain_slug or "").strip()
    if slug:
        return slug.replace("-", " ").title()
    email_local = (identity.admin_email or "").split("@")[0]
    return email_local.replace(".", " ").replace("_", " ").replace("-", " ").title() or "DTA Coach"


def _offer_card_payload(code: str, *, featured: bool = False):
    offer = OFFER_CATALOG.get(code)
    if not offer:
        return None
    billing = offer.get("billing") or offer.get("billing_cycle")
    amount_cents = int(offer.get("amount_cents") or 0)
    if billing == "free":
        price_label = "Free"
    elif billing == "weekly":
        price_label = f"${amount_cents / 100:.0f} / week"
    else:
        price_label = f"${amount_cents / 100:.0f} / month"

    includes_coaching = bool(offer.get("includes_coaching"))
    if code == "macro_calculator_free":
        description = "Get your personalized macro calculations at no cost."
        name = "Macro Calculator"
    elif includes_coaching:
        description = (
            f"Free {int(offer.get('trial_days') or 0)}-day trial for first-time users, then {price_label.lower()}. "
            "Includes food planning plus premium coaching dashboard features. Trial includes 1 meal plan generation per day."
        )
        name = "Meal Plan + Coaching (Premium)"
        if billing == "weekly":
            name = "Meal Plan + Coaching (Weekly Premium)"
        elif billing == "monthly":
            name = "Meal Plan + Coaching (Monthly Premium)"
    else:
        description = (
            f"Free {int(offer.get('trial_days') or 0)}-day trial for first-time users, then {price_label.lower()}. "
            "Includes calculated foods and meal structure. Trial includes 1 meal plan generation per day."
        )
        name = "Meal Plan With Foods (Weekly)" if billing == "weekly" else "Meal Plan With Foods (Monthly)"

    return {
        "code": code,
        "name": name,
        "price_label": price_label,
        "billing": billing,
        "trial_days": int(offer.get("trial_days") or 0),
        "description": description,
        "includes_food_plan": bool(offer.get("includes_food_plan")),
        "includes_coaching": includes_coaching,
        "featured": featured,
        "is_locked": False,
        "lock_reason": "",
    }


def _admin_trial_offer_restricted(identity: AdminIdentity) -> bool:
    User = get_user_model()
    admin_user = User.objects.filter(email__iexact=identity.admin_email, role="admin").first()
    if not admin_user:
        return False

    has_active_trial = admin_user.profiles.filter(is_active=True, is_trial=True).exists()
    if not has_active_trial:
        return False

    active_clients_count = ClientProfile.objects.filter(
        associated_admin=identity,
        is_active=True,
    ).count()
    return active_clients_count >= TRIAL_ADMIN_CLIENT_LIMIT


@api_view(["GET"])
def admin_public_marketing_page(request, slug):
    slug = (slug or "").strip().lower()
    if not slug:
        return _error("INVALID_SLUG", "Missing admin subdomain slug.", status=400)

    identity = AdminIdentity.objects.filter(subdomain_slug=slug).first()
    if not identity:
        return _error("ADMIN_PAGE_NOT_FOUND", "This admin page could not be found.", status=404)

    restrict_paid_offers = _admin_trial_offer_restricted(identity)
    lock_reason = (
        f"This coach is currently on a trial plan and has reached the {TRIAL_ADMIN_CLIENT_LIMIT}-client limit. "
        "Paid plans are temporarily unavailable."
    )

    offer_rows = [
        _offer_card_payload("macro_calculator_free"),
        _offer_card_payload("food_plan_monthly"),
        _offer_card_payload("food_plan_monthly_premium", featured=True),
    ]

    if restrict_paid_offers:
        for row in offer_rows:
            if not row:
                continue
            if row.get("billing") != "free":
                row["is_locked"] = True
                row["lock_reason"] = lock_reason

    offers = [row for row in offer_rows if row]
    if not offers:
        return _error("OFFERS_NOT_CONFIGURED", "No offers are configured right now.", status=503)

    return _ok(
        {
            "admin_page": {
                "slug": slug,
                "brand_name": _display_name_from_identity(identity),
                "headline": identity.marketing_headline or "Personalized Nutrition, Built From Real Food",
                "subheadline": identity.marketing_subheadline or "Use the macro calculator free, or start a 1-month food-based meal plan with a free 3-day trial (1 meal plan generation per day) if you have never tried it before.",
                "marketing_image_url": identity.marketing_image_url,
                "marketing_html": identity.marketing_html,
                "marketing_theme": identity.marketing_theme,
                "custom_css_url": identity.custom_css_url,
                "dev_url": f"{slug}.lvh.me:3000",
                "public_url": f"{slug}.dtameals.com",
            },
            "paid_offers_locked": bool(restrict_paid_offers),
            "offer_lock_reason": lock_reason if restrict_paid_offers else "",
            "offers": offers,
        }
    )
