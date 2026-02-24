from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from django.utils import timezone

from users.client_area.models import ClientPendingSignup, ClientProfile, DiscountCode


VALID_SALE_CHANNELS = {"dta_direct", "admin_white_label", "admin_partner"}
VALID_DISCOUNT_TYPES = {"percent", "fixed_amount"}
VALID_DISCOUNT_SCOPES = {"one_time", "recurring", "either"}

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
    "food_plan_weekly": {
        "billing_cycle": "weekly",
        "trial_days": 5,
        "amount_cents": 500,
        "includes_food_plan": True,
        "includes_coaching": False,
        "premium_dashboard": False,
        "channels": ["dta_direct", "admin_white_label", "admin_partner"],
        "display_name": "DTA Meal Plan With Foods (Weekly)",
    },
    "food_plan_weekly_premium": {
        "billing_cycle": "weekly",
        "trial_days": 5,
        "amount_cents": 1200,
        "includes_food_plan": True,
        "includes_coaching": True,
        "premium_dashboard": True,
        "channels": ["dta_direct", "admin_white_label", "admin_partner"],
        "display_name": "DTA Meal Plan + Coaching (Weekly Premium)",
    },
    "food_plan_monthly": {
        "billing_cycle": "monthly",
        "trial_days": 5,
        "amount_cents": 1500,
        "includes_food_plan": True,
        "includes_coaching": False,
        "premium_dashboard": False,
        "channels": ["dta_direct", "admin_white_label", "admin_partner"],
        "display_name": "DTA Meal Plan With Foods (Monthly)",
    },
    "food_plan_monthly_premium": {
        "billing_cycle": "monthly",
        "trial_days": 5,
        "amount_cents": 3500,
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


def _round_decimal_to_cents(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


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


def _discount_code_matches_list(values: list[str] | None, needle: str) -> bool:
    if not values:
        return True
    normalized = {str(v).strip().lower() for v in values if str(v).strip()}
    return needle.strip().lower() in normalized


def _load_discount_code(code: str | None) -> DiscountCode | None:
    token = str(code or "").strip().upper()
    if not token:
        return None
    return DiscountCode.objects.filter(code=token).first()


def resolve_discount_code(
    *,
    code: str | None,
    offer_code: str,
    sale_channel: str,
    purchase_mode: str,
    associated_admin_id: int | None = None,
) -> DiscountCode | None:
    row = _load_discount_code(code)
    if not row:
        raise QuoteError("INVALID_DISCOUNT_CODE", "Discount code was not found.")
    if not row.is_active:
        raise QuoteError("DISCOUNT_CODE_INACTIVE", "Discount code is inactive.")

    now = timezone.now()
    if row.starts_at and row.starts_at > now:
        raise QuoteError("DISCOUNT_CODE_NOT_STARTED", "Discount code is not active yet.")
    if row.ends_at and row.ends_at < now:
        raise QuoteError("DISCOUNT_CODE_EXPIRED", "Discount code has expired.")
    if row.max_redemptions and row.redeemed_count >= row.max_redemptions:
        raise QuoteError("DISCOUNT_CODE_EXHAUSTED", "Discount code has reached its redemption limit.")

    if row.scope == "one_time" and purchase_mode == "subscription":
        raise QuoteError("DISCOUNT_CODE_SCOPE_MISMATCH", "Discount code is valid only for one-time purchases.")
    if row.scope == "recurring" and purchase_mode == "payment":
        raise QuoteError("DISCOUNT_CODE_SCOPE_MISMATCH", "Discount code is valid only for recurring subscriptions.")

    if not _discount_code_matches_list(row.eligible_offer_codes, offer_code):
        raise QuoteError("DISCOUNT_CODE_NOT_ELIGIBLE_FOR_OFFER", "Discount code is not valid for this plan.")
    if not _discount_code_matches_list(row.eligible_sale_channels, sale_channel):
        raise QuoteError("DISCOUNT_CODE_NOT_ELIGIBLE_FOR_CHANNEL", "Discount code is not valid for this sales channel.")

    if row.associated_admin_id and associated_admin_id and int(row.associated_admin_id) != int(associated_admin_id):
        raise QuoteError("DISCOUNT_CODE_ADMIN_MISMATCH", "Discount code is not valid for this admin.")
    if row.associated_admin_id and not associated_admin_id:
        raise QuoteError("DISCOUNT_CODE_ADMIN_MISMATCH", "Discount code is admin-specific and cannot be used here.")

    return row


def _discount_amount_cents(subtotal_cents: int, code: DiscountCode | None) -> int:
    if not code or subtotal_cents <= 0:
        return 0
    if code.discount_type == "fixed_amount":
        return max(0, min(int(code.amount_cents or 0), subtotal_cents))
    percent = Decimal(str(code.percent_off or "0"))
    if percent <= 0:
        return 0
    raw = (Decimal(subtotal_cents) * percent) / Decimal("100")
    return max(0, min(_round_decimal_to_cents(raw), subtotal_cents))


def _allocate_discount(
    *,
    plan_cents: int,
    coaching_cents: int,
    discount_cents: int,
    purchase_mode: str,
) -> tuple[int, int]:
    discount_left = max(0, int(discount_cents))
    plan_final = int(plan_cents)
    coaching_final = int(coaching_cents)

    # For subscription checkout, apply custom discounts to the recurring plan only.
    if purchase_mode == "subscription":
        applied_to_plan = min(plan_final, discount_left)
        plan_final -= applied_to_plan
        return plan_final, coaching_final

    applied_to_plan = min(plan_final, discount_left)
    plan_final -= applied_to_plan
    discount_left -= applied_to_plan
    if discount_left > 0:
        applied_to_coaching = min(coaching_final, discount_left)
        coaching_final -= applied_to_coaching
    return plan_final, coaching_final


def build_client_purchase_quote(
    *,
    email: str,
    offer_code: str,
    coaching_term: str,
    sale_channel: str,
    purchase_mode: str,
    associated_admin_id: int | None = None,
    discount_code: str | None = None,
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

    applied_discount = None
    if str(discount_code or "").strip():
        applied_discount = resolve_discount_code(
            code=discount_code,
            offer_code=offer_code,
            sale_channel=sale_channel,
            purchase_mode=purchase_mode,
            associated_admin_id=associated_admin_id,
        )

    discount_cents = _discount_amount_cents(subtotal_cents, applied_discount)
    discounted_plan_cents, discounted_coaching_cents = _allocate_discount(
        plan_cents=plan_cents,
        coaching_cents=coaching_addon_cents,
        discount_cents=discount_cents,
        purchase_mode=purchase_mode,
    )
    total_cents = max(0, discounted_plan_cents + discounted_coaching_cents)

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
            "discount_cents": discount_cents,
            "plan_final_cents": discounted_plan_cents,
            "coaching_addon_final_cents": discounted_coaching_cents,
            "total_cents": total_cents,
        },
        "discount": None
        if not applied_discount
        else {
            "code": applied_discount.code,
            "name": applied_discount.name,
            "scope": applied_discount.scope,
            "discount_type": applied_discount.discount_type,
            "percent_off": float(applied_discount.percent_off or 0) if applied_discount.percent_off is not None else None,
            "amount_cents": int(applied_discount.amount_cents or 0),
        },
    }
