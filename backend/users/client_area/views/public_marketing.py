from rest_framework.decorators import api_view

from users.admin_area.models import AdminIdentity


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


@api_view(["GET"])
def admin_public_marketing_page(request, slug):
    slug = (slug or "").strip().lower()
    if not slug:
        return _error("INVALID_SLUG", "Missing admin subdomain slug.", status=400)

    identity = AdminIdentity.objects.filter(subdomain_slug=slug).first()
    if not identity:
        return _error("ADMIN_PAGE_NOT_FOUND", "This admin page could not be found.", status=404)

    offers = [
        {
            "code": "macro_calculator_free",
            "name": "Macro Calculator",
            "price_label": "Free",
            "billing": "free",
            "trial_days": 0,
            "description": "Get your personalized macro calculations at no cost.",
            "includes_food_plan": False,
            "featured": False,
        },
        {
            "code": "food_plan_weekly",
            "name": "Meal Plan With Foods (Weekly)",
            "price_label": "$5 / week",
            "billing": "weekly",
            "trial_days": 5,
            "description": "Free 5-day trial for first-time users, then $5/week. Includes calculated foods and meal structure.",
            "includes_food_plan": True,
            "featured": True,
        },
        {
            "code": "food_plan_monthly",
            "name": "Meal Plan With Foods (Monthly)",
            "price_label": "$15 / month",
            "billing": "monthly",
            "trial_days": 5,
            "description": "Free 5-day trial for first-time users, then $15/month. Best value for consistency.",
            "includes_food_plan": True,
            "featured": False,
        },
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
