from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import get_random_string
from datetime import timedelta
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
import stripe

from users.admin_area.models import AdminIdentity
from users.client_area.models import (
    ClientFoodPreferenceChangeLog,
    ClientMealComboSelection,
    ClientMacroAccessLink,
    ClientPendingSignup,
    ClientProfile,
    ClientQuestionnaireProgress,
    ClientQueuedPlanChange,
)
from users.client_area.services.pricing import (
    OFFER_CATALOG,
    PAID_OFFER_CODES,
    PLAN_ACTIONABLE_OFFER_CODES,
    QuoteError,
    build_client_purchase_quote,
    trial_days_for_offer,
)
from users.client_area.views.api_contract import error, ok, require_client
from core.services.google_oauth import verify_google_id_token
from core.models import MealComboTemplate
from users.client_area.services.results_engine import BuildResultsContext, build_questionnaire_results

stripe.api_key = getattr(settings, "STRIPE_SECRET_KEY", None)
FRONTEND_URL = getattr(settings, "FRONTEND_URL", None) or "https://localhost:3000"

QUESTIONNAIRE_STEPS = [
    "gender",
    "height",
    "weight",
    "date_of_birth",
    "goal",
    "lifestyle",
    "meal_plan_type",
    "workout_days",
    "meal_schedule",
    "training_schedule",
]
WEEK_DAYS = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]


def _stripe_once_discount_from_quote(quote_payload):
    discount = (quote_payload or {}).get("discount") or {}
    amounts = (quote_payload or {}).get("amounts") or {}
    discount_cents = int(amounts.get("discount_cents") or 0)
    if not discount or discount_cents <= 0:
        return None

    discount_type = str(discount.get("discount_type") or "").strip()
    coupon_kwargs = {
        "duration": "once",
        "name": f"App Discount {discount.get('code') or ''}".strip(),
        "metadata": {
            "source": "app_discount_code",
            "code": str(discount.get("code") or ""),
        },
    }
    if discount_type == "percent" and discount.get("percent_off") is not None:
        coupon_kwargs["percent_off"] = float(discount.get("percent_off"))
    else:
        coupon_kwargs["amount_off"] = discount_cents
        coupon_kwargs["currency"] = "usd"

    coupon = stripe.Coupon.create(**coupon_kwargs)
    return {"coupon": coupon.id}

def _is_gmail_email(value):
    email = (value or "").strip().lower()
    return email.endswith("@gmail.com") or email.endswith("@googlemail.com")


def _questionnaire_payload(progress):
    return {
        "status": progress.status,
        "current_step": progress.current_step or QUESTIONNAIRE_STEPS[0],
        "answers": progress.answers_json or {},
        "required_steps": QUESTIONNAIRE_STEPS,
        "completed_at": progress.completed_at,
    }


def _macro_link_questionnaire_payload(link):
    return {
        "status": link.questionnaire_status,
        "current_step": link.questionnaire_current_step or QUESTIONNAIRE_STEPS[0],
        "answers": link.questionnaire_answers_json or {},
        "required_steps": QUESTIONNAIRE_STEPS,
        "completed_at": link.questionnaire_completed_at,
    }


def _trial_days_for_offer(email, offer_code):
    return trial_days_for_offer(email, offer_code)


def _build_client_settings_payload(profile: ClientProfile | None):
    if not profile:
        return None
    trial_eligible = profile.offer_code == "macro_calculator_free"
    queued_changes = [
        {
            "id": q.id,
            "target_offer_code": q.target_offer_code,
            "target_coaching_term": q.target_coaching_term,
            "amount_cents": q.amount_cents,
            "queued_for_period_end_at": q.queued_for_period_end_at,
            "status": q.status,
            "created_at": q.created_at,
        }
        for q in ClientQueuedPlanChange.objects.filter(user=profile.user, status="queued").order_by("-created_at")[:10]
    ]
    return {
        "offer_code": profile.offer_code,
        "billing_cycle": profile.billing_cycle,
        "trial_days": profile.trial_days,
        "amount_cents": profile.amount_cents,
        "includes_food_plan": profile.includes_food_plan,
        "includes_coaching": profile.includes_coaching,
        "coaching_term": profile.coaching_term,
        "coaching_expires_at": profile.coaching_expires_at,
        "is_active": profile.is_active,
        "cancel_at_period_end": bool(getattr(profile, "cancel_at_period_end", False)),
        "sale_channel": profile.sale_channel,
        "associated_admin_slug": profile.associated_admin.subdomain_slug if profile.associated_admin else None,
        "can_start_trial": trial_eligible,
        "queued_changes": queued_changes,
        "available_actions": {
            "start_free_trial": profile.offer_code == "macro_calculator_free",
            "switch_weekly": profile.offer_code != "food_plan_weekly",
            "switch_monthly": profile.offer_code != "food_plan_monthly",
            "add_coaching_1_month": profile.includes_food_plan and profile.coaching_term != "1_month",
            "add_coaching_3_months": profile.includes_food_plan and profile.coaching_term != "3_months",
            "cancel": profile.offer_code in PAID_OFFER_CODES and profile.is_active and not getattr(profile, "cancel_at_period_end", False),
            "reactivate": profile.offer_code in PAID_OFFER_CODES and bool(getattr(profile, "cancel_at_period_end", False)),
        },
    }


def _apply_offer_to_profile(profile: ClientProfile, offer_code: str, *, use_trial_if_eligible=False):
    if offer_code not in OFFER_CATALOG:
        raise ValueError("INVALID_OFFER")
    offer = OFFER_CATALOG[offer_code]
    if offer_code not in PLAN_ACTIONABLE_OFFER_CODES:
        raise ValueError("INVALID_OFFER")

    trial_days = profile.trial_days
    if use_trial_if_eligible and profile.offer_code == "macro_calculator_free" and offer_code in PAID_OFFER_CODES:
        trial_days = offer["trial_days"]
    elif offer_code in PAID_OFFER_CODES:
        trial_days = 0
    else:
        trial_days = 0

    profile.offer_code = offer_code
    profile.billing_cycle = offer["billing_cycle"]
    profile.amount_cents = offer["amount_cents"]
    profile.includes_food_plan = offer["includes_food_plan"]
    profile.includes_coaching = offer["includes_coaching"]
    profile.trial_days = trial_days
    if offer_code in PAID_OFFER_CODES:
        profile.is_active = True
        if hasattr(profile, "cancel_at_period_end"):
            profile.cancel_at_period_end = False
    profile.save(
        update_fields=[
            "offer_code",
            "billing_cycle",
            "amount_cents",
            "includes_food_plan",
            "includes_coaching",
            "trial_days",
            "is_active",
            "cancel_at_period_end",
            "updated_at",
        ]
    )
    return profile


def _apply_coaching_to_profile(profile: ClientProfile, coaching_term: str):
    if coaching_term not in {"none", "1_month", "3_months"}:
        raise ValueError("INVALID_COACHING_TERM")
    profile.includes_coaching = coaching_term != "none"
    profile.coaching_term = coaching_term
    if coaching_term == "none":
        profile.coaching_expires_at = None
    elif coaching_term == "1_month":
        profile.coaching_expires_at = timezone.now() + timedelta(days=30)
    elif coaching_term == "3_months":
        profile.coaching_expires_at = timezone.now() + timedelta(days=90)
    profile.save(update_fields=["includes_coaching", "coaching_term", "coaching_expires_at", "updated_at"])
    return profile


def _serialize_food_preference_builder(progress: ClientQuestionnaireProgress):
    answers = dict(progress.answers_json or {})
    food_pref = answers.get("food_preferences") if isinstance(answers.get("food_preferences"), dict) else {}
    return food_pref or {}


def _serialize_saved_weekly_combo_rows(user):
    rows = (
        ClientMealComboSelection.objects.filter(user=user)
        .select_related("combo_template")
        .order_by("day_of_week", "meal_number")
    )
    weekly = {day: [] for day in WEEK_DAYS}
    for row in rows:
        combo = row.combo_template
        weekly[row.day_of_week].append(
            {
                "protein_1": combo.protein_slot_1,
                "protein_2": combo.protein_slot_2,
                "carbs_1": combo.carb_slot_1,
                "carbs_2": combo.carb_slot_2,
                "fats_1": combo.fat_slot_1,
                "fats_2": combo.fat_slot_2,
                "combo_id": combo.combo_id,
                "combo_match": "matched",
            }
        )
    return weekly


def _extract_weekly_combo_selection_rows(answers):
    meal_schedule = answers.get("meal_schedule") or {}
    meal_days = meal_schedule.get("days") or {}
    food_preferences = answers.get("food_preferences") or {}
    weekly_days = food_preferences.get("weekly_days") or {}

    rows = []
    missing = []
    invalid = []

    for day in WEEK_DAYS:
        expected_count = int(meal_days.get(day) or 0)
        if expected_count not in (3, 4, 5, 6):
            invalid.append({"day": day, "reason": "invalid_meal_count"})
            continue

        day_meals = weekly_days.get(day)
        if not isinstance(day_meals, list):
            missing.append({"day": day, "reason": "missing_day_meals"})
            continue
        if len(day_meals) != expected_count:
            invalid.append(
                {"day": day, "reason": "meal_count_mismatch", "expected": expected_count, "actual": len(day_meals)}
            )
            continue

        for idx, meal in enumerate(day_meals, start=1):
            combo_id = None
            try:
                combo_id = int((meal or {}).get("combo_id") or 0)
            except (TypeError, ValueError):
                combo_id = 0
            if combo_id <= 0:
                invalid.append({"day": day, "meal_number": idx, "reason": "missing_combo_id"})
                continue
            rows.append({"day_of_week": day, "meal_number": idx, "combo_id": combo_id})

    return rows, missing, invalid


def _persist_client_meal_combo_selections(user, answers):
    rows, missing, invalid = _extract_weekly_combo_selection_rows(answers)
    if missing or invalid:
        raise ValueError({"missing": missing, "invalid": invalid})

    combo_ids = sorted({row["combo_id"] for row in rows})
    templates = MealComboTemplate.objects.filter(combo_id__in=combo_ids)
    template_map = {obj.combo_id: obj for obj in templates}
    missing_combo_ids = [combo_id for combo_id in combo_ids if combo_id not in template_map]
    if missing_combo_ids:
        raise LookupError(missing_combo_ids)

    with transaction.atomic():
        ClientMealComboSelection.objects.filter(user=user).delete()
        ClientMealComboSelection.objects.bulk_create(
            [
                ClientMealComboSelection(
                    user=user,
                    day_of_week=row["day_of_week"],
                    meal_number=row["meal_number"],
                    combo_template_id=row["combo_id"],
                )
                for row in rows
            ]
        )
    return len(rows)


@api_view(["POST"])
@permission_classes([AllowAny])
def public_signup_quote(request):
    payload = request.data or {}
    email = (payload.get("email") or "").strip().lower()
    offer_code = (payload.get("offer_code") or "").strip()
    admin_slug = (payload.get("admin_slug") or "").strip().lower()
    discount_code = (payload.get("discount_code") or "").strip()
    coaching_term = (payload.get("coaching_term") or "none").strip()

    if not offer_code:
        return error("MISSING_OFFER_CODE", "Offer code is required.", http_status=400)
    if offer_code not in OFFER_CATALOG:
        return error("INVALID_OFFER", "Offer not recognized.", http_status=400)

    admin = None
    sale_channel = "dta_direct"
    if admin_slug:
        admin = AdminIdentity.objects.filter(subdomain_slug=admin_slug).first()
        if not admin:
            return error("ADMIN_PAGE_NOT_FOUND", "Admin page not found.", http_status=404)
        sale_channel = "admin_white_label"

    offer = OFFER_CATALOG[offer_code]
    if offer.get("billing_cycle") == "free":
        trial_days = _trial_days_for_offer(email, offer_code) if email else 0
        return ok(
            {
                "quote": {
                    "offer_code": offer_code,
                    "offer_display_name": offer.get("display_name") or offer_code,
                    "billing_cycle": offer.get("billing_cycle"),
                    "sale_channel": sale_channel,
                    "purchase_mode": "subscription",
                    "coaching_term": coaching_term,
                    "trial_days": trial_days,
                    "currency": "usd",
                    "entitlements_preview": {
                        "includes_food_plan": bool(offer.get("includes_food_plan")),
                        "includes_coaching": bool(offer.get("includes_coaching")),
                        "has_premium_dashboard": bool(offer.get("premium_dashboard")),
                    },
                    "amounts": {
                        "plan_base_cents": int(offer.get("amount_cents") or 0),
                        "coaching_addon_base_cents": 0,
                        "subtotal_cents": int(offer.get("amount_cents") or 0),
                        "discount_cents": 0,
                        "plan_final_cents": int(offer.get("amount_cents") or 0),
                        "coaching_addon_final_cents": 0,
                        "total_cents": int(offer.get("amount_cents") or 0),
                    },
                    "discount": None,
                }
            }
        )

    try:
        quote = build_client_purchase_quote(
            email=email or "pending@example.com",
            offer_code=offer_code,
            coaching_term=coaching_term,
            sale_channel=sale_channel,
            purchase_mode="subscription",
            associated_admin_id=admin.id if admin else None,
            discount_code=discount_code,
            trial_eligible=bool(email),
        )
    except QuoteError as exc:
        return error(exc.code, exc.message, http_status=400)

    return ok({"quote": quote})


@api_view(["POST"])
@permission_classes([AllowAny])
def start_signup(request):
    """
    Free offer path remains DEV-friendly (creates a pending signup directly).
    Paid offers now require Stripe checkout and return a checkout URL.
    """
    if not getattr(settings, "DEBUG", False):
        return error("FORBIDDEN", "This endpoint is available only in DEBUG mode.", http_status=403)

    payload = request.data or {}
    email = (payload.get("email") or "").strip().lower()
    offer_code = (payload.get("offer_code") or "").strip()
    admin_slug = (payload.get("admin_slug") or "").strip().lower()
    discount_code = (payload.get("discount_code") or "").strip()

    if not email or not offer_code:
        return error("MISSING_FIELDS", "Email and offer_code are required.", http_status=400)
    if offer_code not in OFFER_CATALOG:
        return error("INVALID_OFFER", "Offer not recognized.", http_status=400)

    admin = None
    sale_channel = "dta_direct"
    if admin_slug:
        admin = AdminIdentity.objects.filter(subdomain_slug=admin_slug).first()
        if not admin:
            return error("ADMIN_PAGE_NOT_FOUND", "Admin page not found.", http_status=404)
        sale_channel = "admin_white_label"

    offer = OFFER_CATALOG[offer_code]

    User = get_user_model()
    if User.objects.filter(email=email).exists():
        return error("EMAIL_ALREADY_REGISTERED", "This email already has an account.", http_status=409)

    existing_pending = ClientPendingSignup.objects.filter(email=email).first()
    if existing_pending:
        existing_pending.delete()

    if offer.get("billing_cycle") == "free":
        applied_trial_days = _trial_days_for_offer(email, offer_code)
        pending_amount_cents = int(offer["amount_cents"])
        pending_includes_food_plan = bool(offer["includes_food_plan"])
        pending_includes_coaching = bool(offer["includes_coaching"])
        quote_payload = None
    else:
        if not stripe.api_key:
            return error("STRIPE_NOT_CONFIGURED", "Stripe is not configured on the server.", http_status=500)
        try:
            quote_payload = build_client_purchase_quote(
                email=email,
                offer_code=offer_code,
                coaching_term="none",
                sale_channel=sale_channel,
                purchase_mode="subscription",
                associated_admin_id=admin.id if admin else None,
                discount_code=discount_code,
                trial_eligible=True,
            )
        except QuoteError as exc:
            return error(exc.code, exc.message, http_status=400)
        applied_trial_days = int(quote_payload.get("trial_days") or 0)
        amounts = quote_payload.get("amounts") or {}
        pending_amount_cents = int(amounts.get("total_cents") or offer["amount_cents"])
        ent = quote_payload.get("entitlements_preview") or {}
        pending_includes_food_plan = bool(ent.get("includes_food_plan", offer["includes_food_plan"]))
        pending_includes_coaching = bool(ent.get("includes_coaching", offer["includes_coaching"]))
        if pending_amount_cents <= 0:
            return error(
                "UNSUPPORTED_ZERO_AMOUNT_SUBSCRIPTION",
                "This discount reduces the checkout total to $0.00, which is not supported in the current checkout flow.",
                http_status=400,
            )

        customer = stripe.Customer.create(
            email=email,
            metadata={
                "flow": "public_client_signup_checkout",
                "sale_channel": sale_channel,
                "admin_slug": admin_slug or "",
                "offer_code": offer_code,
            },
        )

        discount = quote_payload.get("discount") or {}
        discount_code_clean = str(discount.get("code") or "").strip()
        product_name = quote_payload.get("offer_display_name") or offer_code
        if discount_code_clean and int((amounts or {}).get("discount_cents") or 0) > 0:
            product_name = f"{product_name} (Special Applied: {discount_code_clean})"

        recurring_interval = "week" if offer["billing_cycle"] == "weekly" else "month"
        success_path = f"/start/{admin_slug}/plans" if admin_slug else "/user_plans"
        cancel_path = success_path

        subscription_data = {
            "metadata": {
                "flow": "public_client_signup_checkout",
                "signup_email": email,
                "sale_channel": sale_channel,
                "admin_slug": admin_slug or "",
                "admin_id": str(admin.id if admin else ""),
                "offer_code": offer_code,
                "discount_code": discount_code_clean,
                "trial_days": str(applied_trial_days),
                "amount_cents": str(pending_amount_cents),
                "includes_food_plan": "1" if pending_includes_food_plan else "0",
                "includes_coaching": "1" if pending_includes_coaching else "0",
            }
        }
        if applied_trial_days > 0:
            subscription_data["trial_period_days"] = int(applied_trial_days)

        stripe_discount = _stripe_once_discount_from_quote(quote_payload)
        allow_promotion_codes = not bool(stripe_discount)
        line_unit_amount = int(offer.get("amount_cents") or pending_amount_cents)

        session_kwargs = dict(
            mode="subscription",
            payment_method_types=["card"],
            customer=customer.id,
            allow_promotion_codes=allow_promotion_codes,
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": product_name},
                        "unit_amount": line_unit_amount,
                        "recurring": {"interval": recurring_interval},
                    },
                    "quantity": 1,
                }
            ],
            subscription_data=subscription_data,
            metadata={
                "flow": "public_client_signup_checkout",
                "signup_email": email,
                "sale_channel": sale_channel,
                "admin_slug": admin_slug or "",
                "admin_id": str(admin.id if admin else ""),
                "offer_code": offer_code,
                "discount_code": discount_code_clean,
                "trial_days": str(applied_trial_days),
                "amount_cents": str(pending_amount_cents),
            },
            success_url=f"{FRONTEND_URL}{success_path}?signup_checkout=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}{cancel_path}?signup_checkout=cancel",
        )
        if stripe_discount:
            session_kwargs["discounts"] = [stripe_discount]

        session = stripe.checkout.Session.create(**session_kwargs)

        return ok(
            {
                "message": "Redirecting to secure checkout.",
                "checkout_url": session.url,
                "checkout_session_id": session.id,
                "offer": {"code": offer_code, **offer, "trial_days": applied_trial_days},
                "quote": quote_payload,
                "sale_channel": sale_channel,
                "admin_slug": admin_slug or None,
            },
            http_status=201,
        )

    token = get_random_string(64)
    pending = ClientPendingSignup.objects.create(
        email=email,
        token=token,
        admin=admin,
        sale_channel=sale_channel,
        offer_code=offer_code,
        billing_cycle=offer["billing_cycle"],
        trial_days=applied_trial_days,
        amount_cents=pending_amount_cents,
        includes_food_plan=pending_includes_food_plan,
        includes_coaching=pending_includes_coaching,
        registration_link_printed_at=timezone.now(),
    )

    registration_link = f"{FRONTEND_URL}/client_register?token={pending.token}"
    print("\n" + "=" * 60)
    print("📩 Client registration email (simulated):")
    print(f"To: {email}")
    print("Subject: Finish setting up your DTA account")
    print(f"➡️ Click to register:\n{registration_link}")
    print("=" * 60 + "\n")

    return ok(
        {
            "message": "Signup started (DEV). Registration link created.",
            "registration_link": registration_link,
            "offer": {"code": offer_code, **offer, "trial_days": applied_trial_days},
            "quote": quote_payload,
            "sale_channel": sale_channel,
            "admin_slug": admin_slug or None,
        },
        http_status=201,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def register_client(request):
    payload = request.data or {}
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password")
    token = (payload.get("token") or "").strip()
    credential = (payload.get("credential") or "").strip()

    if not email or not token or (not password and not credential):
        return error("MISSING_FIELDS", "Email, token, and password or Google credential are required.", http_status=400)
    if _is_gmail_email(email) and not credential:
        return error("GOOGLE_REQUIRED", "Gmail accounts must continue with Google.", http_status=400)

    if credential:
        try:
            google_payload = verify_google_id_token(credential)
        except RuntimeError as exc:
            return error("GOOGLE_CONFIG_ERROR", str(exc), http_status=500)
        except ValueError as exc:
            return error("INVALID_GOOGLE_TOKEN", str(exc), http_status=401)
        google_email = (google_payload.get("email") or "").strip().lower()
        email_verified = bool(google_payload.get("email_verified"))
        if not google_email or not email_verified:
            return error("GOOGLE_EMAIL_UNVERIFIED", "Google email is missing or not verified.", http_status=401)
        if google_email != email:
            return error("EMAIL_TOKEN_MISMATCH", "Google account email does not match this registration link.", http_status=400)

    pending = ClientPendingSignup.objects.filter(token=token).first()
    if not pending:
        return error("INVALID_TOKEN", "Invalid or expired registration token.", http_status=404)
    if pending.email != email:
        return error("EMAIL_TOKEN_MISMATCH", "This token does not match the provided email.", http_status=400)

    User = get_user_model()
    if User.objects.filter(username=email).exists():
        return error("USER_EXISTS", "User already exists.", http_status=409)

    if credential:
        user = User.objects.create_user(username=email, email=email)
        user.set_unusable_password()
    else:
        user = User.objects.create_user(username=email, email=email, password=password)
    user.role = "client"
    user.is_staff = False
    user.subscription_status = "admin_inactive"  # unused for clients, kept compatible with existing field choices
    user.save()

    ClientProfile.objects.create(
        user=user,
        associated_admin=pending.admin,
        sale_channel=pending.sale_channel,
        offer_code=pending.offer_code,
        billing_cycle=pending.billing_cycle,
        trial_days=pending.trial_days,
        amount_cents=pending.amount_cents,
        includes_food_plan=pending.includes_food_plan,
        includes_coaching=pending.includes_coaching,
        is_active=True,
    )
    ClientQuestionnaireProgress.objects.create(
        user=user,
        status="not_started",
        current_step=QUESTIONNAIRE_STEPS[0],
        answers_json={},
    )

    pending.delete()

    refresh = RefreshToken.for_user(user)
    refresh["email"] = user.email
    refresh["role"] = user.role

    return ok(
        {
            "success": True,
            "message": "Client account created.",
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "email": user.email,
            "role": user.role,
        },
        http_status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def pending_signup_preview(request, token):
    pending = ClientPendingSignup.objects.filter(token=token).first()
    if not pending:
        return error("INVALID_TOKEN", "Invalid or expired registration token.", http_status=404)
    return ok(
        {
            "pending_signup": {
                "email": pending.email,
                "offer_code": pending.offer_code,
                "billing_cycle": pending.billing_cycle,
                "trial_days": pending.trial_days,
                "amount_cents": pending.amount_cents,
                "sale_channel": pending.sale_channel,
                "admin_slug": pending.admin.subdomain_slug if pending.admin else None,
            }
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def macro_access_preview(request, token):
    link = ClientMacroAccessLink.objects.select_related("admin").filter(token=token).first()
    if not link:
        return error("INVALID_TOKEN", "Invalid or expired macro calculator link.", http_status=404)
    link.last_opened_at = timezone.now()
    link.save(update_fields=["last_opened_at"])
    return ok(
        {
            "macro_access": {
                "email": link.email,
                "sale_channel": link.sale_channel,
                "admin_slug": link.admin.subdomain_slug if link.admin else None,
                "questionnaire": _macro_link_questionnaire_payload(link),
                "results": build_questionnaire_results(
                    BuildResultsContext(
                        answers=link.questionnaire_answers_json or {},
                        admin_identity=link.admin,
                    )
                ) if link.questionnaire_status == "completed" else None,
            }
        }
    )


@api_view(["GET", "PATCH"])
@permission_classes([AllowAny])
def macro_access_questionnaire(request, token):
    link = ClientMacroAccessLink.objects.filter(token=token).first()
    if not link:
        return error("INVALID_TOKEN", "Invalid or expired macro calculator link.", http_status=404)

    if request.method == "GET":
        return ok({"questionnaire": _macro_link_questionnaire_payload(link)})

    payload = request.data or {}
    step_key = (payload.get("step_key") or "").strip()
    answer = payload.get("answer")
    next_step = (payload.get("next_step") or "").strip()
    if step_key not in QUESTIONNAIRE_STEPS:
        return error("INVALID_STEP", "Unknown questionnaire step.", http_status=400)

    answers = dict(link.questionnaire_answers_json or {})
    answers[step_key] = answer
    link.questionnaire_answers_json = answers
    link.questionnaire_status = "in_progress"
    link.questionnaire_current_step = next_step if next_step in QUESTIONNAIRE_STEPS else step_key
    link.save(update_fields=["questionnaire_answers_json", "questionnaire_status", "questionnaire_current_step"])
    return ok({"message": "Draft saved.", "questionnaire": _macro_link_questionnaire_payload(link)})


@api_view(["POST"])
@permission_classes([AllowAny])
def macro_access_questionnaire_submit(request, token):
    link = ClientMacroAccessLink.objects.filter(token=token).first()
    if not link:
        return error("INVALID_TOKEN", "Invalid or expired macro calculator link.", http_status=404)

    answers = dict(link.questionnaire_answers_json or {})
    missing = [step for step in QUESTIONNAIRE_STEPS if step not in answers or answers.get(step) in (None, "", [])]
    if missing:
        return error(
            "MISSING_REQUIRED_STEPS",
            "Questionnaire is incomplete.",
            http_status=400,
            details={"missing_steps": missing},
        )
    link.questionnaire_status = "completed"
    link.questionnaire_current_step = QUESTIONNAIRE_STEPS[-1]
    link.questionnaire_completed_at = timezone.now()
    link.save(update_fields=["questionnaire_status", "questionnaire_current_step", "questionnaire_completed_at"])
    return ok(
        {
            "message": "Questionnaire submitted.",
            "questionnaire": _macro_link_questionnaire_payload(link),
            "results": build_questionnaire_results(
                BuildResultsContext(
                    answers=link.questionnaire_answers_json or {},
                    admin_identity=link.admin,
                )
            ),
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def client_dashboard(request):
    auth_error = require_client(request)
    if auth_error:
        return auth_error

    profile = ClientProfile.objects.filter(user=request.user).select_related("associated_admin").first()
    progress, _ = ClientQuestionnaireProgress.objects.get_or_create(
        user=request.user,
        defaults={"status": "not_started", "current_step": QUESTIONNAIRE_STEPS[0], "answers_json": {}},
    )

    return ok(
        {
            "client": {
                "email": request.user.email,
                "offer_code": profile.offer_code if profile else None,
                "billing_cycle": profile.billing_cycle if profile else None,
                "trial_days": profile.trial_days if profile else 0,
                "includes_food_plan": bool(profile and profile.includes_food_plan),
                "includes_coaching": bool(profile and profile.includes_coaching),
                "sale_channel": profile.sale_channel if profile else "dta_direct",
                "associated_admin_slug": profile.associated_admin.subdomain_slug if profile and profile.associated_admin else None,
            },
            "questionnaire": _questionnaire_payload(progress),
            "results": build_questionnaire_results(
                BuildResultsContext(
                    answers=progress.answers_json or {},
                    admin_identity=profile.associated_admin if profile else None,
                )
            ) if progress.status == "completed" else None,
            "settings": _build_client_settings_payload(profile),
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def client_settings_view(request):
    auth_error = require_client(request)
    if auth_error:
        return auth_error
    profile = ClientProfile.objects.filter(user=request.user).select_related("associated_admin").first()
    if not profile:
        return error("CLIENT_PROFILE_NOT_FOUND", "Client profile not found.", http_status=404)
    return ok({"settings": _build_client_settings_payload(profile)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def client_plan_action(request):
    auth_error = require_client(request)
    if auth_error:
        return auth_error
    profile = ClientProfile.objects.filter(user=request.user).select_related("associated_admin").first()
    if not profile:
        return error("CLIENT_PROFILE_NOT_FOUND", "Client profile not found.", http_status=404)

    action = (request.data or {}).get("action") or ""
    action = str(action).strip()

    if action in {"start_free_trial", "switch_weekly", "switch_monthly", "add_coaching_1_month", "add_coaching_3_months"}:
        return error(
            "SECURE_CHECKOUT_REQUIRED",
            "Use Secure Checkout to start, upgrade, or add coaching to your plan.",
            http_status=400,
        )

    if action == "cancel_subscription":
        if profile.offer_code not in PAID_OFFER_CODES:
            return error("INVALID_ACTION", "No paid subscription to cancel.", http_status=400)
        if not profile.stripe_subscription_id:
            return error("STRIPE_SUBSCRIPTION_NOT_FOUND", "No Stripe subscription found for this client.", http_status=400)
        if stripe.api_key:
            try:
                sub = stripe.Subscription.retrieve(profile.stripe_subscription_id)
                if sub.get("status") in ("active", "trialing", "past_due") and not bool(sub.get("cancel_at_period_end")):
                    sub = stripe.Subscription.modify(profile.stripe_subscription_id, cancel_at_period_end=True)
                period_end = sub.get("current_period_end")
                profile.is_active = True  # access continues until Stripe period end
                profile.cancel_at_period_end = True
                profile.save(update_fields=["is_active", "cancel_at_period_end", "updated_at"])
                return ok(
                    {
                        "message": "Subscription will cancel at period end.",
                        "stripe": {
                            "status": sub.get("status"),
                            "cancel_at_period_end": bool(sub.get("cancel_at_period_end")),
                            "current_period_end": period_end,
                        },
                        "settings": _build_client_settings_payload(profile),
                    }
                )
            except Exception as exc:
                return error("STRIPE_CANCEL_FAILED", f"Could not cancel subscription: {exc}", http_status=400)
        profile.is_active = False
        profile.cancel_at_period_end = True
        profile.save(update_fields=["is_active", "cancel_at_period_end", "updated_at"])
        return ok({"message": "Subscription canceled (local fallback).", "settings": _build_client_settings_payload(profile)})

    if action == "reactivate_subscription":
        if profile.offer_code not in PAID_OFFER_CODES:
            return error("INVALID_ACTION", "No paid subscription to reactivate.", http_status=400)
        if not profile.stripe_subscription_id:
            return error("STRIPE_SUBSCRIPTION_NOT_FOUND", "No Stripe subscription found for this client.", http_status=400)
        if stripe.api_key:
            try:
                sub = stripe.Subscription.modify(profile.stripe_subscription_id, cancel_at_period_end=False)
                profile.is_active = True
                profile.cancel_at_period_end = False
                profile.save(update_fields=["is_active", "cancel_at_period_end", "updated_at"])
                return ok(
                    {
                        "message": "Subscription reactivated (auto-renew restored).",
                        "stripe": {
                            "status": sub.get("status"),
                            "cancel_at_period_end": bool(sub.get("cancel_at_period_end")),
                            "current_period_end": sub.get("current_period_end"),
                        },
                        "settings": _build_client_settings_payload(profile),
                    }
                )
            except Exception as exc:
                return error("STRIPE_REACTIVATE_FAILED", f"Could not reactivate subscription: {exc}", http_status=400)
        profile.is_active = True
        profile.cancel_at_period_end = False
        profile.save(update_fields=["is_active", "cancel_at_period_end", "updated_at"])
        return ok({"message": "Subscription reactivated (local fallback).", "settings": _build_client_settings_payload(profile)})

    return error("INVALID_ACTION", "Unsupported plan action.", http_status=400)


@api_view(["GET", "PUT"])
@permission_classes([IsAuthenticated])
def client_food_preferences(request):
    auth_error = require_client(request)
    if auth_error:
        return auth_error

    profile = ClientProfile.objects.filter(user=request.user).select_related("associated_admin").first()
    if not profile:
        return error("CLIENT_PROFILE_NOT_FOUND", "Client profile not found.", http_status=404)
    progress, _ = ClientQuestionnaireProgress.objects.get_or_create(
        user=request.user,
        defaults={"status": "not_started", "current_step": QUESTIONNAIRE_STEPS[0], "answers_json": {}},
    )
    if progress.status != "completed":
        return error("QUESTIONNAIRE_REQUIRED", "Complete the onboarding questionnaire first.", http_status=400)

    if request.method == "GET":
        builder_value = _serialize_food_preference_builder(progress)
        if not builder_value:
            builder_value = {
                "weekly_days": _serialize_saved_weekly_combo_rows(request.user),
            }
        return ok(
            {
                "food_preferences": {
                    "builder_value": builder_value,
                    "meal_schedule_days": (progress.answers_json or {}).get("meal_schedule", {}).get("days", {}),
                    "results": build_questionnaire_results(
                        BuildResultsContext(
                            answers=progress.answers_json or {},
                            admin_identity=profile.associated_admin if profile else None,
                        )
                    ),
                }
            }
        )

    if not profile.includes_food_plan:
        return error("PLAN_UPGRADE_REQUIRED", "Upgrade to a food plan to customize meals.", http_status=403)

    payload = request.data or {}
    builder_value = payload.get("builder_value")
    if not isinstance(builder_value, dict):
        return error("INVALID_PAYLOAD", "builder_value must be an object.", http_status=400)

    answers = dict(progress.answers_json or {})
    previous_food_preferences = answers.get("food_preferences") if isinstance(answers.get("food_preferences"), dict) else {}
    answers["food_preferences"] = builder_value
    progress.answers_json = answers
    progress.save(update_fields=["answers_json", "updated_at"])

    food_preferences_changed = previous_food_preferences != builder_value

    try:
        saved_count = _persist_client_meal_combo_selections(request.user, answers)
    except ValueError as exc:
        return error("INVALID_MEAL_COMBO_SELECTIONS", "Meal selections are incomplete or invalid.", http_status=400, details=exc.args[0] if exc.args else None)
    except LookupError as exc:
        return error("UNKNOWN_MEAL_COMBO_IDS", "One or more selected meal combos no longer exist.", http_status=400, details={"combo_ids": list(exc.args[0]) if exc.args else []})

    if food_preferences_changed:
        ClientFoodPreferenceChangeLog.objects.create(
            user=request.user,
            client_profile=profile,
            before_json=previous_food_preferences or {},
            after_json=builder_value,
        )

    return ok(
        {
            "message": "Food preferences saved.",
            "saved_meal_combo_selections": saved_count,
            "food_preferences_changed": food_preferences_changed,
            "meal_plan_regeneration_required": bool(food_preferences_changed),
        }
    )


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def questionnaire_status_or_draft(request):
    auth_error = require_client(request)
    if auth_error:
        return auth_error

    progress, _ = ClientQuestionnaireProgress.objects.get_or_create(
        user=request.user,
        defaults={"status": "not_started", "current_step": QUESTIONNAIRE_STEPS[0], "answers_json": {}},
    )

    if request.method == "GET":
        return ok({"questionnaire": _questionnaire_payload(progress)})

    payload = request.data or {}
    step_key = (payload.get("step_key") or "").strip()
    answer = payload.get("answer")
    next_step = (payload.get("next_step") or "").strip()

    if step_key not in QUESTIONNAIRE_STEPS:
        return error("INVALID_STEP", "Unknown questionnaire step.", http_status=400)

    answers = dict(progress.answers_json or {})
    answers[step_key] = answer
    progress.answers_json = answers
    progress.status = "in_progress"
    progress.current_step = next_step if next_step in QUESTIONNAIRE_STEPS else step_key
    progress.save(update_fields=["answers_json", "status", "current_step", "updated_at"])

    return ok({"message": "Draft saved.", "questionnaire": _questionnaire_payload(progress)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def questionnaire_submit(request):
    auth_error = require_client(request)
    if auth_error:
        return auth_error

    progress, _ = ClientQuestionnaireProgress.objects.get_or_create(
        user=request.user,
        defaults={"status": "not_started", "current_step": QUESTIONNAIRE_STEPS[0], "answers_json": {}},
    )
    answers = dict(progress.answers_json or {})

    missing = [step for step in QUESTIONNAIRE_STEPS if step not in answers or answers.get(step) in (None, "", [])]
    if missing:
        return error(
            "MISSING_REQUIRED_STEPS",
            "Questionnaire is incomplete.",
            http_status=400,
            details={"missing_steps": missing},
        )

    progress.status = "completed"
    progress.current_step = QUESTIONNAIRE_STEPS[-1]
    progress.completed_at = timezone.now()
    progress.save(update_fields=["status", "current_step", "completed_at", "updated_at"])
    profile = ClientProfile.objects.filter(user=request.user).select_related("associated_admin").first()
    return ok(
        {
            "message": "Questionnaire submitted.",
            "questionnaire": _questionnaire_payload(progress),
            "results": build_questionnaire_results(
                BuildResultsContext(
                    answers=progress.answers_json or {},
                    admin_identity=profile.associated_admin if profile else None,
                )
            ),
        }
    )
