from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import get_random_string
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from users.admin_area.models import AdminIdentity
from users.client_area.models import (
    ClientMealComboSelection,
    ClientMacroAccessLink,
    ClientPendingSignup,
    ClientProfile,
    ClientQuestionnaireProgress,
)
from users.client_area.views.api_contract import error, ok, require_client
from core.services.google_oauth import verify_google_id_token
from core.models import MealComboTemplate


OFFER_CATALOG = {
    "macro_calculator_free": {
        "billing_cycle": "free",
        "trial_days": 0,
        "amount_cents": 0,
        "includes_food_plan": False,
        "includes_coaching": False,
    },
    "food_plan_weekly": {
        "billing_cycle": "weekly",
        "trial_days": 5,
        "amount_cents": 500,
        "includes_food_plan": True,
        "includes_coaching": False,
    },
    "food_plan_monthly": {
        "billing_cycle": "monthly",
        "trial_days": 5,
        "amount_cents": 1500,
        "includes_food_plan": True,
        "includes_coaching": False,
    },
}

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
    "food_preferences",
]
WEEK_DAYS = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]

PAID_OFFER_CODES = {"food_plan_weekly", "food_plan_monthly"}


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
    offer = OFFER_CATALOG[offer_code]
    if offer["billing_cycle"] == "free":
        return 0

    # ClientProfile stores email through the related user; pending signups covers in-progress prior trials.
    has_used_trial = ClientProfile.objects.filter(
        user__email__iexact=email,
        offer_code__in=PAID_OFFER_CODES,
        trial_days__gt=0,
    ).exists() or ClientPendingSignup.objects.filter(
        email__iexact=email,
        offer_code__in=PAID_OFFER_CODES,
        trial_days__gt=0,
    ).exists()
    return 0 if has_used_trial else offer["trial_days"]


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
def start_signup(request):
    """
    DEV-friendly stand-in for Stripe checkout completion so you can test the full questionnaire flow now.
    Creates a pending signup and returns/prints a registration link.
    """
    if not getattr(settings, "DEBUG", False):
        return error("FORBIDDEN", "This endpoint is available only in DEBUG mode.", http_status=403)

    payload = request.data or {}
    email = (payload.get("email") or "").strip().lower()
    offer_code = (payload.get("offer_code") or "").strip()
    admin_slug = (payload.get("admin_slug") or "").strip().lower()

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

    applied_trial_days = _trial_days_for_offer(email, offer_code)
    token = get_random_string(64)
    pending = ClientPendingSignup.objects.create(
        email=email,
        token=token,
        admin=admin,
        sale_channel=sale_channel,
        offer_code=offer_code,
        billing_cycle=offer["billing_cycle"],
        trial_days=applied_trial_days,
        amount_cents=offer["amount_cents"],
        includes_food_plan=offer["includes_food_plan"],
        includes_coaching=offer["includes_coaching"],
        registration_link_printed_at=timezone.now(),
    )

    registration_link = f"http://localhost:3000/client_register?token={pending.token}"
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
    combo_rows, combo_missing, combo_invalid = _extract_weekly_combo_selection_rows(answers)
    if combo_missing or combo_invalid:
        return error(
            "INVALID_MEAL_COMBO_SELECTIONS",
            "Meal selections are incomplete or invalid.",
            http_status=400,
            details={"missing": combo_missing, "invalid": combo_invalid},
        )

    link.questionnaire_status = "completed"
    link.questionnaire_current_step = QUESTIONNAIRE_STEPS[-1]
    link.questionnaire_completed_at = timezone.now()
    link.save(update_fields=["questionnaire_status", "questionnaire_current_step", "questionnaire_completed_at"])
    return ok(
        {
            "message": "Questionnaire submitted.",
            "questionnaire": _macro_link_questionnaire_payload(link),
            "meal_combo_rows_ready": len(combo_rows),
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
                "associated_admin_slug": profile.associated_admin.subdomain_slug if profile and profile.associated_admin else None,
            },
            "questionnaire": _questionnaire_payload(progress),
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

    try:
        saved_selection_count = _persist_client_meal_combo_selections(request.user, answers)
    except ValueError as exc:
        return error(
            "INVALID_MEAL_COMBO_SELECTIONS",
            "Meal selections are incomplete or invalid.",
            http_status=400,
            details=exc.args[0] if exc.args else None,
        )
    except LookupError as exc:
        missing_combo_ids = list(exc.args[0]) if exc.args else []
        return error(
            "UNKNOWN_MEAL_COMBO_IDS",
            "One or more selected meal combos no longer exist.",
            http_status=400,
            details={"combo_ids": missing_combo_ids},
        )

    progress.status = "completed"
    progress.current_step = QUESTIONNAIRE_STEPS[-1]
    progress.completed_at = timezone.now()
    progress.save(update_fields=["status", "current_step", "completed_at", "updated_at"])
    return ok(
        {
            "message": "Questionnaire submitted.",
            "questionnaire": _questionnaire_payload(progress),
            "saved_meal_combo_selections": saved_selection_count,
        }
    )
