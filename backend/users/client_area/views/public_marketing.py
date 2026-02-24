from rest_framework.decorators import api_view

from users.admin_area.models import AdminIdentity
from users.client_area.services.pricing import OFFER_CATALOG


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
    offer = OFFER_CATALOG[code]
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
            "Includes food planning plus premium coaching dashboard features."
        )
        name = "Meal Plan + Coaching (Premium)"
        if billing == "weekly":
            name = "Meal Plan + Coaching (Weekly Premium)"
        elif billing == "monthly":
            name = "Meal Plan + Coaching (Monthly Premium)"
    else:
        description = (
            f"Free {int(offer.get('trial_days') or 0)}-day trial for first-time users, then {price_label.lower()}. "
            "Includes calculated foods and meal structure."
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
    }


@api_view(["GET"])
def admin_public_marketing_page(request, slug):
    slug = (slug or "").strip().lower()
    if not slug:
        return _error("INVALID_SLUG", "Missing admin subdomain slug.", status=400)

    identity = AdminIdentity.objects.filter(subdomain_slug=slug).first()
    if not identity:
        return _error("ADMIN_PAGE_NOT_FOUND", "This admin page could not be found.", status=404)

    offers = [
        _offer_card_payload("macro_calculator_free"),
        _offer_card_payload("food_plan_weekly", featured=True),
        _offer_card_payload("food_plan_weekly_premium"),
        _offer_card_payload("food_plan_monthly"),
        _offer_card_payload("food_plan_monthly_premium"),
    ]

    return _ok(
        {
            "admin_page": {
                "slug": slug,
                "brand_name": _display_name_from_identity(identity),
                "headline": "Personalized Nutrition, Built From Real Food",
                "subheadline": "Use the macro calculator free, or start a food-based meal plan with a free 5-day trial if you have never tried it before.",
                "dev_url": f"{slug}.lvh.me:3000",
                "public_url": f"{slug}.dtameals.com",
            },
            "offers": offers,
        }
    )
