from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from users.client_area.models import ClientPendingSignup, ClientProfile


VALID_SALE_CHANNELS = {"dta_direct", "admin_white_label", "admin_partner"}
OFFER_CATALOG: dict[str, dict[str, Any]] = {
    "macro_calculator_free": {
        "billing_cycle": "free",
        "trial_days": 0,
        "amount_cents": 0,
        "includes_food_plan": False,
        "includes_coaching": False,
        "premium_dashboard": False,
        "channels": ["dta_direct", "admin_white_label", "admin_partner"],
        "display_name": "Macro Calculator (Free)",
    },
    "food_plan_monthly": {
        "billing_cycle": "monthly",
        "trial_days": 3,
        "amount_cents": 1500,
        "stripe_price_id": "price_1T4ePgAYzIGw9RTd15eXzRtz",
        "includes_food_plan": True,
        "includes_coaching": False,
        "premium_dashboard": False,
        "channels": ["dta_direct", "admin_white_label", "admin_partner"],
        "display_name": "DTA Meal Plan With Foods (Monthly)",
    },
    "food_plan_monthly_premium": {
        "billing_cycle": "monthly",
        "trial_days": 3,
        "amount_cents": 3500,
        "stripe_price_id": "price_1T4eQAAYzIGw9RTdyqD4UdkD",
        "includes_food_plan": True,
        "includes_coaching": True,
        "premium_dashboard": True,
        "channels": ["dta_direct", "admin_white_label", "admin_partner"],
        "display_name": "DTA Meal Plan + Coaching (Monthly Premium)",
    },
}

PAID_OFFER_CODES = {code for code, cfg in OFFER_CATALOG.items() if cfg["billing_cycle"] != "free"}
PLAN_ACTIONABLE_OFFER_CODES = set(OFFER_CATALOG.keys())

COACHING_ADDON_CENTS = {
    "none": 0,
    "1_month": 3000,
    "3_months": 5000,
}


@dataclass
class QuoteError(Exception):
    code: str
    message: str


def _normalized_channel(value: str | None) -> str:
    channel = (value or "dta_direct").strip().lower()
    return channel if channel in VALID_SALE_CHANNELS else "dta_direct"


def validate_offer_code(offer_code: str, *, sale_channel: str | None = None, allow_free: bool = False) -> dict[str, Any]:
    offer = OFFER_CATALOG.get((offer_code or "").strip())
    if not offer:
        raise QuoteError("INVALID_OFFER", "Offer not recognized.")
    if not allow_free and offer_code not in PAID_OFFER_CODES:
        raise QuoteError("INVALID_OFFER", "Select a valid paid plan.")
    channel = _normalized_channel(sale_channel)
    allowed_channels = set(offer.get("channels") or [])
    if allowed_channels and channel not in allowed_channels:
        raise QuoteError("OFFER_NOT_AVAILABLE_FOR_CHANNEL", "Offer is not available for this sales channel.")
    return offer


def validate_coaching_term(coaching_term: str | None) -> str:
    term = str(coaching_term or "none").strip()
    if term not in COACHING_ADDON_CENTS:
        raise QuoteError("INVALID_COACHING_TERM", "Select a valid coaching option.")
    return term


def trial_days_for_offer(email: str, offer_code: str) -> int:
    offer = validate_offer_code(offer_code, allow_free=True)
    if offer["billing_cycle"] == "free":
        return 0

    has_used_trial = ClientProfile.objects.filter(
        user__email__iexact=email,
        offer_code__in=PAID_OFFER_CODES,
        trial_days__gt=0,
    ).exists() or ClientPendingSignup.objects.filter(
        email__iexact=email,
        offer_code__in=PAID_OFFER_CODES,
        trial_days__gt=0,
        status=ClientPendingSignup.STATUS_PENDING,
    ).exists()
    return 0 if has_used_trial else int(offer.get("trial_days") or 0)


def entitlements_for_offer(*, offer_code: str, coaching_term: str = "none") -> dict[str, Any]:
    offer = validate_offer_code(offer_code, allow_free=True)
    coaching_term = validate_coaching_term(coaching_term)
    includes_coaching = bool(offer.get("includes_coaching")) or coaching_term != "none"
    return {
        "includes_food_plan": bool(offer.get("includes_food_plan")),
        "includes_coaching": includes_coaching,
        "has_premium_dashboard": bool(offer.get("premium_dashboard")) or includes_coaching,
        "can_message_coach": includes_coaching,
        "can_upload_progress_photos": includes_coaching,
        "can_use_stats_journal": includes_coaching,
    }


def build_client_purchase_quote(
    *,
    email: str,
    offer_code: str,
    coaching_term: str,
    sale_channel: str,
    purchase_mode: str,
    trial_eligible: bool = False,
) -> dict[str, Any]:
    if purchase_mode not in {"subscription", "payment"}:
        raise QuoteError("INVALID_PURCHASE_MODE", "Unsupported purchase mode.")

    sale_channel = _normalized_channel(sale_channel)
    offer = validate_offer_code(offer_code, sale_channel=sale_channel, allow_free=False)
    coaching_term = validate_coaching_term(coaching_term)

    plan_cents = int(offer.get("amount_cents") or 0)
    includes_coaching_offer = bool(offer.get("includes_coaching"))
    coaching_addon_cents = 0 if includes_coaching_offer else int(COACHING_ADDON_CENTS.get(coaching_term, 0))
    subtotal_cents = plan_cents + coaching_addon_cents

    total_cents = subtotal_cents

    trial_days = trial_days_for_offer(email, offer_code) if trial_eligible else 0
    entitlements = entitlements_for_offer(offer_code=offer_code, coaching_term=coaching_term)

    return {
        "offer_code": offer_code,
        "offer_display_name": offer.get("display_name"),
        "billing_cycle": offer.get("billing_cycle"),
        "sale_channel": sale_channel,
        "purchase_mode": purchase_mode,
        "coaching_term": coaching_term,
        "includes_coaching_offer": includes_coaching_offer,
        "entitlements_preview": entitlements,
        "trial_days": int(trial_days),
        "currency": "usd",
        "amounts": {
            "plan_base_cents": plan_cents,
            "coaching_addon_base_cents": coaching_addon_cents,
            "subtotal_cents": subtotal_cents,
            "plan_final_cents": plan_cents,
            "coaching_addon_final_cents": coaching_addon_cents,
            "total_cents": total_cents,
        },
    }
