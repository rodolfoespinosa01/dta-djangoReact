from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import get_random_string
from datetime import timedelta
import logging
from urllib.parse import quote_plus
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
from core.services.meal_combo_lookup import (
    find_meal_combo_id_by_slots,
    get_supported_combo_slot_values,
    normalize_slots_to_supported_combo_values,
)
from core.services.meal_combo_shape_policy import select_meal_combo_template_for_target
from core.models import MealComboTemplate
from users.client_area.services.results_engine import BuildResultsContext, build_questionnaire_results
from core.services.theme_preferences import normalize_theme

stripe.api_key = getattr(settings, "STRIPE_SECRET_KEY", None)
FRONTEND_URL = getattr(settings, "FRONTEND_URL", None) or "https://localhost:3000"
logger = logging.getLogger(__name__)

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
    "protein_shake",
]
WEEK_DAYS = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
MEAL_COMBO_SLOT_KEYS = ["protein_1", "protein_2", "carbs_1", "carbs_2", "fats_1", "fats_2"]
QUESTIONNAIRE_OPTIONAL_STEPS = {"protein_shake"}
QUESTIONNAIRE_IMMUTABLE_AFTER_COMPLETION = {"gender", "height"}
QUESTIONNAIRE_REQUIRES_REGEN_FIELDS = {
    "weight",
    "date_of_birth",
    "goal",
    "lifestyle",
    "meal_plan_type",
    "workout_days",
    "meal_schedule",
    "training_schedule",
    "protein_shake",
}
QUESTIONNAIRE_ALLOWED_VALUES = {
    "gender": {"male", "female"},
    "goal": {"lose", "maintain", "gain"},
    "lifestyle": {"low", "moderate", "high"},
    "meal_plan_type": {"standard", "carb_cycling", "keto"},
}

TRIAL_ADMIN_CLIENT_LIMIT = 5


def _required_questionnaire_steps():
    return [step for step in QUESTIONNAIRE_STEPS if step not in QUESTIONNAIRE_OPTIONAL_STEPS]

def _is_gmail_email(value):
    email = (value or "").strip().lower()
    return email.endswith("@gmail.com") or email.endswith("@googlemail.com")


def _is_pending_expired(pending: ClientPendingSignup) -> bool:
    return bool(pending.expires_at and pending.expires_at <= timezone.now())


def _questionnaire_payload(progress):
    return {
        "status": progress.status,
        "current_step": progress.current_step or QUESTIONNAIRE_STEPS[0],
        "answers": progress.answers_json or {},
        "required_steps": QUESTIONNAIRE_STEPS,
        "completed_at": progress.completed_at,
    }


def _food_preferences_completed(progress):
    answers = progress.answers_json or {}
    food_preferences = answers.get("food_preferences")
    return isinstance(food_preferences, dict) and bool(food_preferences)


def _onboarding_payload(profile, progress):
    requires_food_preferences = bool(profile and profile.includes_food_plan)
    questionnaire_completed = progress.status == "completed"
    food_preferences_completed = _food_preferences_completed(progress)
    next_step = "dashboard"
    if not questionnaire_completed:
        next_step = "questionnaire"
    elif requires_food_preferences and not food_preferences_completed:
        next_step = "food_preferences"

    return {
        "questionnaire_completed": questionnaire_completed,
        "requires_food_preferences": requires_food_preferences,
        "food_preferences_completed": food_preferences_completed,
        "next_step": next_step,
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


def _admin_trial_client_stats(admin_identity: AdminIdentity | None):
    if not admin_identity:
        return {
            "trial_active": False,
            "active_clients": 0,
            "pending_signups": 0,
        }

    User = get_user_model()
    admin_user = User.objects.filter(email__iexact=admin_identity.admin_email, role="admin").first()
    if not admin_user:
        return {
            "trial_active": False,
            "active_clients": 0,
            "pending_signups": 0,
        }

    has_active_trial = admin_user.profiles.filter(is_active=True, is_trial=True).exists()
    if not has_active_trial:
        return {
            "trial_active": False,
            "active_clients": 0,
            "pending_signups": 0,
        }

    active_clients = ClientProfile.objects.filter(associated_admin=admin_identity).count()
    pending_signups = ClientPendingSignup.objects.filter(
        admin=admin_identity,
        status=ClientPendingSignup.STATUS_PENDING,
    ).count()
    return {
        "trial_active": True,
        "active_clients": active_clients,
        "pending_signups": pending_signups,
    }


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
        "theme_preference": normalize_theme(getattr(profile, "theme_preference", "light")),
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


def _normalize_meal_combo_payload(meal, supported_slot_values=None):
    source = meal if isinstance(meal, dict) else {}
    normalized_slots = normalize_slots_to_supported_combo_values(
        {key: source.get(key) for key in MEAL_COMBO_SLOT_KEYS},
        supported_values=supported_slot_values,
    )
    combo_id = find_meal_combo_id_by_slots(**normalized_slots)
    return {
        **source,
        **normalized_slots,
        "combo_id": int(combo_id) if combo_id else None,
        "combo_match": "matched" if combo_id else "not_found",
    }


def _meal_count_for_day_from_answers(answers, day):
    meal_days = ((answers.get("meal_schedule") or {}).get("days") or {}) if isinstance(answers, dict) else {}
    try:
        meal_count = int(meal_days.get(day) or 3)
    except (TypeError, ValueError):
        meal_count = 3
    return meal_count if meal_count in (3, 4, 5, 6) else 3


def _clamp_meal_number(value, meal_count):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = 1
    return max(1, min(meal_count, parsed))


def _protein_shake_meals_by_day(answers):
    protein_shake = answers.get("protein_shake") if isinstance(answers, dict) else {}
    if (
        not isinstance(protein_shake, dict)
        or protein_shake.get("enabled") is not True
        or protein_shake.get("counts_as_meal") is not True
    ):
        return {}
    days_payload = protein_shake.get("days") if isinstance(protein_shake.get("days"), dict) else {}
    selected_by_day = {}
    if days_payload:
        for day, payload in days_payload.items():
            if isinstance(payload, dict) and payload.get("enabled", True) is True:
                selected_by_day[day] = payload.get("selected_meal")
    else:
        selected_by_day = protein_shake.get("selected_meals_by_day") if isinstance(protein_shake.get("selected_meals_by_day"), dict) else {}
    fallback = protein_shake.get("selected_meal") or 1
    return {
        day: _clamp_meal_number(value, _meal_count_for_day_from_answers(answers, day))
        for day, value in selected_by_day.items()
        if day in WEEK_DAYS
    } if days_payload else {
        day: _clamp_meal_number(selected_by_day.get(day, fallback), _meal_count_for_day_from_answers(answers, day))
        for day in WEEK_DAYS
    }


def _protein_shake_meal_payload(source=None):
    source = source if isinstance(source, dict) else {}
    return {
        **source,
        "meal_type": "protein_shake",
        "is_protein_shake": True,
        "protein_1": "-",
        "protein_2": "-",
        "carbs_1": "-",
        "carbs_2": "-",
        "fats_1": "-",
        "fats_2": "-",
        "combo_id": None,
        "combo_match": "protein_shake",
    }


def _normalize_food_preference_builder(builder_value, answers=None):
    if not isinstance(builder_value, dict):
        return {}

    normalized = dict(builder_value)
    supported_slot_values = get_supported_combo_slot_values()

    if isinstance(normalized.get("default_day_meals"), list):
        normalized["default_day_meals"] = [
            _normalize_meal_combo_payload(meal, supported_slot_values) for meal in normalized["default_day_meals"]
        ]

    weekly_days = normalized.get("weekly_days")
    if isinstance(weekly_days, dict):
        normalized["weekly_days"] = {
            day: [_normalize_meal_combo_payload(meal, supported_slot_values) for meal in meals]
            if isinstance(meals, list)
            else meals
            for day, meals in weekly_days.items()
        }

    saved_templates = normalized.get("saved_templates")
    if isinstance(saved_templates, list):
        normalized["saved_templates"] = [
            {
                **template,
                "meals": [_normalize_meal_combo_payload(meal, supported_slot_values) for meal in template.get("meals", [])]
                if isinstance(template, dict) and isinstance(template.get("meals"), list)
                else template.get("meals", []) if isinstance(template, dict) else [],
            }
            if isinstance(template, dict)
            else template
            for template in saved_templates
        ]

    return normalized


def _meal_targets_from_day_payload(day_payload):
    targets = {}
    if not isinstance(day_payload, dict):
        return targets
    for row in day_payload.get("meal_macro_splits") or []:
        if not isinstance(row, dict):
            continue
        try:
            meal_number = int(row.get("meal_number") or 0)
        except (TypeError, ValueError):
            continue
        if meal_number < 1:
            continue
        grams = row.get("grams") if isinstance(row.get("grams"), dict) else {}
        targets[meal_number] = {
            "protein": grams.get("protein_g") or 0,
            "carbs": grams.get("carbs_g") or 0,
            "fats": grams.get("fats_g") or 0,
        }
    return targets


def _training_adjacent_meals(day_payload):
    raw = str((day_payload or {}).get("training_before_meal") or "").strip().lower()
    if not raw.startswith("before_meal_"):
        return set()
    try:
        post_workout_meal = int(raw.split("_")[-1])
    except (TypeError, ValueError):
        return set()
    if post_workout_meal < 1:
        return set()
    meals = {post_workout_meal}
    if post_workout_meal > 1:
        meals.add(post_workout_meal - 1)
    return meals


def _combo_payload_from_template(combo, source_meal):
    return {
        **(source_meal if isinstance(source_meal, dict) else {}),
        "protein_1": combo.protein_slot_1,
        "protein_2": combo.protein_slot_2,
        "carbs_1": combo.carb_slot_1,
        "carbs_2": combo.carb_slot_2,
        "fats_1": combo.fat_slot_1,
        "fats_2": combo.fat_slot_2,
        "combo_id": combo.combo_id,
        "combo_match": "matched",
    }


def _combo_id_from_meal(meal):
    try:
        return int((meal or {}).get("combo_id") or 0)
    except (TypeError, ValueError):
        return 0


def _apply_combo_shape_policy_to_food_preferences(builder_value, results, answers=None):
    if not isinstance(builder_value, dict) or not isinstance(results, dict):
        return builder_value

    weekly_days = builder_value.get("weekly_days")
    shake_meals = _protein_shake_meals_by_day(answers if isinstance(answers, dict) else {})
    result_days = {
        (row or {}).get("day"): row
        for row in (results.get("weekly_days") or [])
        if isinstance(row, dict) and (row or {}).get("day")
    }
    if not isinstance(weekly_days, dict) or not result_days:
        return builder_value

    combo_ids = sorted(
        {
            _combo_id_from_meal(meal)
            for meals in weekly_days.values()
            if isinstance(meals, list)
            for meal in meals
            if isinstance(meal, dict) and _combo_id_from_meal(meal) > 0
        }
    )
    templates = {combo.combo_id: combo for combo in MealComboTemplate.objects.filter(combo_id__in=combo_ids)}
    next_builder = {**builder_value, "weekly_days": dict(weekly_days)}
    debug_rows = {}

    for day, meals in weekly_days.items():
        day_payload = result_days.get(day)
        if not day_payload or not isinstance(meals, list):
            continue
        targets = _meal_targets_from_day_payload(day_payload)
        training_adjacent = _training_adjacent_meals(day_payload)
        patched_meals = []
        for idx, meal in enumerate(meals, start=1):
            if not isinstance(meal, dict):
                patched_meals.append(meal)
                continue
            if shake_meals.get(day) == idx or meal.get("is_protein_shake") is True:
                patched_meals.append(_protein_shake_meal_payload(meal))
                continue
            saved_combo = templates.get(_combo_id_from_meal(meal))
            target = targets.get(idx)
            if not saved_combo or not target:
                patched_meals.append(meal)
                continue
            decision = select_meal_combo_template_for_target(
                saved_combo=saved_combo,
                meal_target=target,
                is_training_adjacent=idx in training_adjacent,
                selected_slots=meal,
            )
            patched_meals.append(_combo_payload_from_template(decision.combo, meal))
            debug_rows[f"{day}:{idx}"] = {
                "day": day,
                "meal_number": idx,
                "protein_target": str(target.get("protein")),
                "carb_target": str(target.get("carbs")),
                "is_training_adjacent": idx in training_adjacent,
                "preferred_protein_structure": decision.preferred_shape.protein_structure,
                "preferred_carb_structure": decision.preferred_shape.carb_structure,
                "candidate_count_before_filtering": decision.candidate_count_before_filtering,
                "candidate_count_after_filtering": decision.candidate_count_after_filtering,
                "chosen_combo_id": decision.combo.combo_id,
                "chosen_protein_slot_1": decision.combo.protein_slot_1,
                "chosen_protein_slot_2": decision.combo.protein_slot_2,
                "chosen_carb_slot_1": decision.combo.carb_slot_1,
                "chosen_carb_slot_2": decision.combo.carb_slot_2,
                "fallback_reason": decision.fallback_reason,
            }
            logger.info(
                "Saved food preference combo shape selection: day=%s meal=%s protein_target=%s carb_target=%s "
                "training_adjacent=%s preferred_protein=%s preferred_carb=%s candidates_before=%s "
                "candidates_after=%s chosen_combo_id=%s protein_slots=%s/%s carb_slots=%s/%s fallback_reason=%s",
                day,
                idx,
                target.get("protein"),
                target.get("carbs"),
                idx in training_adjacent,
                decision.preferred_shape.protein_structure,
                decision.preferred_shape.carb_structure,
                decision.candidate_count_before_filtering,
                decision.candidate_count_after_filtering,
                decision.combo.combo_id,
                decision.combo.protein_slot_1,
                decision.combo.protein_slot_2,
                decision.combo.carb_slot_1,
                decision.combo.carb_slot_2,
                decision.fallback_reason,
            )
        next_builder["weekly_days"][day] = patched_meals

    if debug_rows:
        next_builder["combo_shape_debug"] = debug_rows
    return next_builder


def _extract_weekly_combo_selection_rows(answers):
    meal_schedule = answers.get("meal_schedule") or {}
    meal_days = meal_schedule.get("days") or {}
    food_preferences = answers.get("food_preferences") or {}
    weekly_days = food_preferences.get("weekly_days") or {}
    shake_meals = _protein_shake_meals_by_day(answers)

    rows = []
    missing = []
    invalid = []
    supported_slot_values = get_supported_combo_slot_values()

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
            if shake_meals.get(day) == idx or (isinstance(meal, dict) and meal.get("is_protein_shake") is True):
                continue
            normalized_meal = _normalize_meal_combo_payload(meal, supported_slot_values)
            combo_id = normalized_meal.get("combo_id")
            if not combo_id:
                invalid.append({"day": day, "meal_number": idx, "reason": "missing_combo_id"})
                continue
            rows.append({"day_of_week": day, "meal_number": idx, "combo_id": combo_id})

    return rows, missing, invalid


def _normalize_questionnaire_answer(step_key, answer, current_answers):
    if step_key == "workout_days":
        if not isinstance(answer, list):
            return None, {"reason": "workout_days_must_be_array"}
        selected = []
        seen = set()
        for day in answer:
            normalized = str(day or "").strip().lower()
            if normalized in WEEK_DAYS and normalized not in seen:
                selected.append(normalized)
                seen.add(normalized)
        return selected, None

    if step_key == "meal_schedule":
        if not isinstance(answer, dict):
            return None, {"reason": "meal_schedule_must_be_object"}
        existing_days = (answer.get("days") or {}) if isinstance(answer.get("days"), dict) else {}
        normalized_days = {}
        for day in WEEK_DAYS:
            try:
                value = int(existing_days.get(day))
            except (TypeError, ValueError):
                value = 3
            if value not in (3, 4, 5, 6):
                value = 3
            normalized_days[day] = value

        default_meals = answer.get("default_meals")
        try:
            default_meals = int(default_meals)
        except (TypeError, ValueError):
            default_meals = normalized_days[WEEK_DAYS[0]]
        if default_meals not in (3, 4, 5, 6):
            default_meals = normalized_days[WEEK_DAYS[0]]

        mode = str(answer.get("mode") or "").strip().lower()
        if mode not in {"same", "custom"}:
            mode = "same" if len({normalized_days[d] for d in WEEK_DAYS}) == 1 else "custom"

        return {
            "mode": mode,
            "default_meals": default_meals,
            "days": normalized_days,
        }, None

    if step_key == "training_schedule":
        if not isinstance(answer, dict):
            return None, {"reason": "training_schedule_must_be_object"}
        workout_days = current_answers.get("workout_days") or []
        if not isinstance(workout_days, list):
            workout_days = []
        workout_days = [str(d or "").strip().lower() for d in workout_days if str(d or "").strip().lower() in WEEK_DAYS]
        meal_days = ((current_answers.get("meal_schedule") or {}).get("days") or {})
        normalized = {}
        for day in workout_days:
            raw_value = str(answer.get(day) or "").strip().lower()
            if not raw_value.startswith("before_meal_"):
                continue
            try:
                meal_num = int(raw_value.split("_")[-1])
            except (TypeError, ValueError):
                continue
            try:
                meal_count = int(meal_days.get(day) or 0)
            except (TypeError, ValueError):
                meal_count = 0
            if meal_num < 1 or meal_num > meal_count:
                continue
            normalized[day] = f"before_meal_{meal_num}"
        return normalized, None

    if step_key == "protein_shake":
        disabled_value = {"enabled": False, "counts_as_meal": True}
        if answer in (None, "", []) or (isinstance(answer, dict) and answer.get("enabled") is not True):
            return disabled_value, None
        if not isinstance(answer, dict):
            return None, {"reason": "protein_shake_must_be_object"}

        meal_days = ((current_answers.get("meal_schedule") or {}).get("days") or {})
        training_schedule = current_answers.get("training_schedule") or {}
        valid_timings = {"pre_workout", "post_workout", "other"}

        def meal_count_for_day(day):
            try:
                count = int(meal_days.get(day) or 3)
            except (TypeError, ValueError):
                count = 3
            return count if count in (3, 4, 5, 6) else 3

        def training_meal_for_day(day):
            raw_value = str((training_schedule or {}).get(day) or "").strip().lower()
            if not raw_value.startswith("before_meal_"):
                return None
            try:
                return int(raw_value.split("_")[-1])
            except (TypeError, ValueError):
                return None

        def normalize_timing(value, fallback="other"):
            timing = str(value or "").strip().lower()
            return timing if timing in valid_timings else fallback

        def selected_for_day(day, timing, raw_selected, enabled=None):
            meal_count = meal_count_for_day(day)
            training_meal = training_meal_for_day(day)
            if not training_meal and timing in {"pre_workout", "post_workout"}:
                return {"enabled": True, "timing": "other", "selected_meal": 1} if enabled is True else {"enabled": False, "timing": "other", "selected_meal": 1}
            if enabled is False:
                return {"enabled": False, "timing": "other", "selected_meal": 1}
            if timing == "post_workout":
                return {"enabled": True, "timing": timing, "selected_meal": _clamp_meal_number(training_meal, meal_count)}
            if timing == "pre_workout":
                return {"enabled": True, "timing": timing, "selected_meal": _clamp_meal_number(max(1, training_meal - 1), meal_count)}
            return {"enabled": True, "timing": "other", "selected_meal": _clamp_meal_number(raw_selected, meal_count)}

        def timing_from_legacy(payload):
            if payload.get("mode") == "extra_shake":
                timing_mode = str(payload.get("timing_mode") or "").strip().lower()
                if timing_mode == "pre_workout":
                    return "pre_workout"
                if timing_mode in {"post_workout", "recommended"}:
                    return "post_workout"
                return "other"
            return normalize_timing(payload.get("placement_mode") or payload.get("default_timing"), "post_workout")

        schedule_mode = str(answer.get("schedule_mode") or "").strip().lower()
        if schedule_mode not in {"same", "custom"}:
            schedule_mode = "custom" if isinstance(answer.get("days"), dict) or isinstance(answer.get("selected_meals_by_day"), dict) else "same"

        default_timing = timing_from_legacy(answer)
        default_selected_meal = answer.get("default_selected_meal", answer.get("selected_meal", 1))
        raw_days = answer.get("days") if isinstance(answer.get("days"), dict) else {}
        legacy_by_day = answer.get("selected_meals_by_day") if isinstance(answer.get("selected_meals_by_day"), dict) else {}
        has_legacy_by_day = not raw_days and bool(legacy_by_day)

        days = {}
        for day in WEEK_DAYS:
            raw_day = raw_days.get(day) if isinstance(raw_days.get(day), dict) else {}
            training_meal = training_meal_for_day(day)
            if schedule_mode == "custom":
                timing = normalize_timing(raw_day.get("timing") or answer.get("placement_mode"), default_timing)
                raw_selected = raw_day.get("selected_meal", legacy_by_day.get(day, default_selected_meal))
                enabled = raw_day.get("enabled")
                if enabled is None:
                    enabled = bool(training_meal or has_legacy_by_day)
            else:
                timing = default_timing
                raw_selected = default_selected_meal
                enabled = default_timing == "other" or bool(training_meal)
            days[day] = selected_for_day(day, timing, raw_selected, enabled)

        selected_by_day = {
            day: days[day]["selected_meal"]
            for day in WEEK_DAYS
            if days[day].get("enabled") is True
        }
        selected_meal_day = next((day for day in WEEK_DAYS if training_meal_for_day(day)), WEEK_DAYS[0])
        normalized_default_selected_meal = _clamp_meal_number(
            default_selected_meal,
            meal_count_for_day(selected_meal_day),
        )

        return {
            "enabled": True,
            "counts_as_meal": True,
            "schedule_mode": schedule_mode,
            "default_timing": default_timing,
            "default_selected_meal": normalized_default_selected_meal,
            "days": days,
            "placement_mode": default_timing if schedule_mode == "same" else "other",
            "selected_meal": selected_by_day.get(selected_meal_day, 1),
            "selected_meals_by_day": selected_by_day,
        }, None

    if step_key in {"goal", "lifestyle", "meal_plan_type", "gender"} and isinstance(answer, str):
        return answer.strip().lower(), None

    if step_key == "date_of_birth" and answer is not None:
        return str(answer).strip(), None

    return answer, None


def _normalize_public_questionnaire_answers(raw_answers):
    if not isinstance(raw_answers, dict):
        return None, ["answers"], [{"step": "answers", "reason": "answers_must_be_object"}]

    normalized = {}
    invalid = []
    for step in QUESTIONNAIRE_STEPS:
        if step not in raw_answers or raw_answers.get(step) in (None, "", []):
            continue
        normalized_answer, normalize_error = _normalize_questionnaire_answer(step, raw_answers.get(step), normalized)
        if normalize_error:
            invalid.append({"step": step, **normalize_error})
            continue
        if step in QUESTIONNAIRE_ALLOWED_VALUES and normalized_answer not in QUESTIONNAIRE_ALLOWED_VALUES[step]:
            invalid.append({"step": step, "reason": "unsupported_value"})
            continue
        normalized[step] = normalized_answer

    if "protein_shake" not in normalized:
        normalized["protein_shake"], _ = _normalize_questionnaire_answer("protein_shake", None, normalized)

    missing = [step for step in _required_questionnaire_steps() if step not in normalized or normalized.get(step) in (None, "", [])]
    return normalized, missing, invalid


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
                        "plan_final_cents": int(offer.get("amount_cents") or 0),
                        "coaching_addon_final_cents": 0,
                        "total_cents": int(offer.get("amount_cents") or 0),
                    },
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

    existing_pending = ClientPendingSignup.objects.filter(
        email__iexact=email,
        status=ClientPendingSignup.STATUS_PENDING,
    ).first()
    if existing_pending:
        existing_pending.status = ClientPendingSignup.STATUS_SUPERSEDED
        existing_pending.save(update_fields=["status"])

    if admin and offer_code != "macro_calculator_free":
        trial_stats = _admin_trial_client_stats(admin)
        if trial_stats["trial_active"]:
            reserved_slots = int(trial_stats["active_clients"]) + int(trial_stats["pending_signups"])
            if reserved_slots >= TRIAL_ADMIN_CLIENT_LIMIT:
                return error(
                    "ADMIN_TRIAL_CLIENT_LIMIT_REACHED",
                    "Trial admins can sign up up to 5 clients. Upgrade to continue adding more clients.",
                    http_status=403,
                    details={
                        "client_limit": TRIAL_ADMIN_CLIENT_LIMIT,
                        "active_clients": int(trial_stats["active_clients"]),
                        "pending_signups": int(trial_stats["pending_signups"]),
                    },
                )

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
        customer = stripe.Customer.create(
            email=email,
            metadata={
                "flow": "public_client_signup_checkout",
                "sale_channel": sale_channel,
                "admin_slug": admin_slug or "",
                "offer_code": offer_code,
            },
        )

        stripe_price_id = str(offer.get("stripe_price_id") or "").strip()
        if not stripe_price_id:
            return error("STRIPE_PRICE_NOT_CONFIGURED", "Stripe price is not configured for this plan.", http_status=500)

        success_path = "/client_signup_success"
        cancel_path = f"/start/{admin_slug}/plans" if admin_slug else "/user_plans"
        success_query = f"signup_checkout=success&session_id={{CHECKOUT_SESSION_ID}}&signup_email={quote_plus(email)}"
        if admin_slug:
            success_query = f"{success_query}&admin_slug={quote_plus(admin_slug)}"

        subscription_data = {
            "metadata": {
                "flow": "public_client_signup_checkout",
                "signup_email": email,
                "sale_channel": sale_channel,
                "admin_slug": admin_slug or "",
                "admin_id": str(admin.id if admin else ""),
                "offer_code": offer_code,
                "trial_days": str(applied_trial_days),
                "amount_cents": str(pending_amount_cents),
                "includes_food_plan": "1" if pending_includes_food_plan else "0",
                "includes_coaching": "1" if pending_includes_coaching else "0",
            }
        }
        if applied_trial_days > 0:
            subscription_data["trial_period_days"] = int(applied_trial_days)

        session_kwargs = dict(
            mode="subscription",
            payment_method_types=["card"],
            customer=customer.id,
            allow_promotion_codes=True,
            line_items=[
                {
                    "price": stripe_price_id,
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
                "trial_days": str(applied_trial_days),
                "amount_cents": str(pending_amount_cents),
            },
            success_url=f"{FRONTEND_URL}{success_path}?{success_query}",
            cancel_url=f"{FRONTEND_URL}{cancel_path}?signup_checkout=cancel",
        )

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
    registration_link = f"{FRONTEND_URL}/client_register?token={token}"
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
        registration_link=registration_link,
        status=ClientPendingSignup.STATUS_PENDING,
        registration_link_printed_at=timezone.now(),
    )

    print("\n" + "=" * 60)
    print("📩 Client registration email (simulated):")
    print(f"To: {email}")
    print("Subject: Finish setting up your DTA account")
    print(f"➡️ Click to register:\n{registration_link}")
    print("=" * 60 + "\n")

    response_payload = {
        "message": "Signup started (DEV). Registration link created.",
        "registration_link": registration_link,
        "offer": {"code": offer_code, **offer, "trial_days": applied_trial_days},
        "quote": quote_payload,
        "sale_channel": sale_channel,
        "admin_slug": admin_slug or None,
    }
    if getattr(settings, "DEBUG", False):
        response_payload["debug_registration_link"] = registration_link

    return ok(response_payload, http_status=201)


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

    pending = ClientPendingSignup.objects.filter(
        token=token,
        status=ClientPendingSignup.STATUS_PENDING,
    ).first()
    if not pending:
        return error("INVALID_TOKEN", "Invalid or expired registration token.", http_status=404)
    if _is_pending_expired(pending):
        pending.status = ClientPendingSignup.STATUS_EXPIRED
        pending.save(update_fields=["status"])
        return error("INVALID_TOKEN", "Invalid or expired registration token.", http_status=404)
    if pending.email != email:
        return error("EMAIL_TOKEN_MISMATCH", "This token does not match the provided email.", http_status=400)

    if pending.admin and pending.offer_code != "macro_calculator_free":
        trial_stats = _admin_trial_client_stats(pending.admin)
        if trial_stats["trial_active"] and int(trial_stats["active_clients"]) >= TRIAL_ADMIN_CLIENT_LIMIT:
            return error(
                "ADMIN_TRIAL_CLIENT_LIMIT_REACHED",
                "Trial admins can sign up up to 5 clients. Upgrade to continue adding more clients.",
                http_status=403,
                details={
                    "client_limit": TRIAL_ADMIN_CLIENT_LIMIT,
                    "active_clients": int(trial_stats["active_clients"]),
                },
            )

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
    pending_answers = pending.questionnaire_answers_json if isinstance(pending.questionnaire_answers_json, dict) else {}
    ClientQuestionnaireProgress.objects.create(
        user=user,
        status="completed" if pending_answers else "not_started",
        current_step=QUESTIONNAIRE_STEPS[-1] if pending_answers else QUESTIONNAIRE_STEPS[0],
        answers_json=pending_answers,
        completed_at=timezone.now() if pending_answers else None,
    )

    pending.used_at = timezone.now()
    pending.status = ClientPendingSignup.STATUS_COMPLETED
    pending.save(update_fields=["used_at", "status"])

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
    pending = ClientPendingSignup.objects.filter(
        token=token,
        status=ClientPendingSignup.STATUS_PENDING,
    ).first()
    if not pending:
        return error("INVALID_TOKEN", "Invalid or expired registration token.", http_status=404)
    if _is_pending_expired(pending):
        pending.status = ClientPendingSignup.STATUS_EXPIRED
        pending.save(update_fields=["status"])
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
    normalized_answer, normalize_error = _normalize_questionnaire_answer(step_key, answer, answers)
    if normalize_error:
        return error(
            "INVALID_STEP_ANSWER",
            "The provided answer is invalid for this questionnaire step.",
            http_status=400,
            details={"step_key": step_key, **normalize_error},
        )
    answers[step_key] = normalized_answer
    if step_key in {"meal_schedule", "training_schedule"} and "protein_shake" in answers:
        answers["protein_shake"], _ = _normalize_questionnaire_answer("protein_shake", answers.get("protein_shake"), answers)
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
    if "protein_shake" not in answers:
        answers["protein_shake"], _ = _normalize_questionnaire_answer("protein_shake", None, answers)
        link.questionnaire_answers_json = answers
    else:
        normalized_shake, normalize_error = _normalize_questionnaire_answer("protein_shake", answers.get("protein_shake"), answers)
        if normalize_error:
            return error(
                "INVALID_STEP_ANSWER",
                "The provided answer is invalid for this questionnaire step.",
                http_status=400,
                details={"step_key": "protein_shake", **normalize_error},
            )
        answers["protein_shake"] = normalized_shake
        link.questionnaire_answers_json = answers
    missing = [step for step in _required_questionnaire_steps() if step not in answers or answers.get(step) in (None, "", [])]
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
    link.save(update_fields=["questionnaire_answers_json", "questionnaire_status", "questionnaire_current_step", "questionnaire_completed_at"])
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


@api_view(["POST"])
@permission_classes([AllowAny])
def public_macro_calculator(request):
    payload = request.data or {}
    email = (payload.get("email") or "").strip().lower()
    if not email:
        return error("MISSING_EMAIL", "Email is required to send your macro results link.", http_status=400)
    try:
        validate_email(email)
    except ValidationError:
        return error("INVALID_EMAIL", "Enter a valid email address.", http_status=400)

    answers, missing, invalid = _normalize_public_questionnaire_answers(payload.get("answers"))
    if invalid:
        return error(
            "INVALID_QUESTIONNAIRE_ANSWERS",
            "One or more questionnaire answers are invalid.",
            http_status=400,
            details={"invalid_answers": invalid},
        )
    if missing:
        return error(
            "MISSING_REQUIRED_STEPS",
            "Questionnaire is incomplete.",
            http_status=400,
            details={"missing_steps": missing},
        )

    admin_slug = (payload.get("admin_slug") or "").strip().lower()
    admin_identity = AdminIdentity.objects.filter(subdomain_slug=admin_slug).first() if admin_slug else None
    if admin_slug and not admin_identity:
        return error("ADMIN_PAGE_NOT_FOUND", "Admin page not found.", http_status=404)

    User = get_user_model()
    if User.objects.filter(email=email).exists():
        return error("EMAIL_ALREADY_REGISTERED", "This email already has an account. Log in to view your dashboard.", http_status=409)

    results = build_questionnaire_results(BuildResultsContext(answers=answers or {}, admin_identity=admin_identity))
    if not results:
        return error(
            "UNABLE_TO_CALCULATE_MACROS",
            "We could not calculate macros from these answers.",
            http_status=400,
        )

    existing_pending = ClientPendingSignup.objects.filter(
        email__iexact=email,
        status=ClientPendingSignup.STATUS_PENDING,
    ).first()
    if existing_pending:
        existing_pending.status = ClientPendingSignup.STATUS_SUPERSEDED
        existing_pending.save(update_fields=["status"])

    offer = OFFER_CATALOG["macro_calculator_free"]
    token = get_random_string(64)
    registration_link = f"{FRONTEND_URL}/client_register?token={token}"
    expires_at = timezone.now() + timedelta(days=7)
    pending = ClientPendingSignup.objects.create(
        email=email,
        token=token,
        admin=admin_identity,
        sale_channel="admin_white_label" if admin_identity else "dta_direct",
        offer_code="macro_calculator_free",
        billing_cycle=offer["billing_cycle"],
        trial_days=0,
        amount_cents=int(offer["amount_cents"]),
        includes_food_plan=bool(offer["includes_food_plan"]),
        includes_coaching=bool(offer["includes_coaching"]),
        registration_link=registration_link,
        expires_at=expires_at,
        status=ClientPendingSignup.STATUS_PENDING,
        registration_link_printed_at=timezone.now(),
        questionnaire_answers_json=answers or {},
        questionnaire_results_json=results or {},
    )

    print("\n" + "=" * 60)
    print("📩 Public macro calculator registration email (simulated):")
    print(f"To: {email}")
    print("Subject: Create your DTA account to view your macro results")
    print(f"➡️ Click to register and view macros:\n{registration_link}")
    print(f"Expires: {expires_at.isoformat()}")
    print("=" * 60 + "\n")

    return ok(
        {
            "message": "Check your email to create your account and view your macro results.",
            "pending_signup": {
                "email": pending.email,
                "offer_code": pending.offer_code,
                "expires_at": pending.expires_at,
            },
            **({"debug_registration_link": registration_link} if getattr(settings, "DEBUG", False) else {}),
        },
        http_status=201,
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


    admin_user_id = None
    admin_identity = profile.associated_admin if profile and profile.associated_admin else None
    # If no associated_admin and B2C, use default DTA admin
    if not admin_identity and profile and profile.sale_channel == 'dta_direct':
        admin_identity = AdminIdentity.objects.filter(admin_email='admin@dta.com').first()
    if admin_identity and admin_identity.admin_email:
        from core.models import CustomUser
        try:
            admin_user = CustomUser.objects.get(email=admin_identity.admin_email, role='admin')
            admin_user_id = admin_user.id
        except CustomUser.DoesNotExist:
            admin_user_id = None

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
                "associated_admin_user_id": admin_user_id,
            },
            "questionnaire": _questionnaire_payload(progress),
            "onboarding": _onboarding_payload(profile, progress),
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
        answers = dict(progress.answers_json or {})
        normalized_shake, _ = _normalize_questionnaire_answer("protein_shake", answers.get("protein_shake"), answers)
        if answers.get("protein_shake") != normalized_shake:
            answers["protein_shake"] = normalized_shake
            progress.answers_json = answers
            progress.save(update_fields=["answers_json", "updated_at"])
        builder_value = _serialize_food_preference_builder(progress)
        if not builder_value:
            builder_value = {
                "weekly_days": _serialize_saved_weekly_combo_rows(request.user),
            }
        normalized_builder_value = _normalize_food_preference_builder(builder_value, answers=answers)
        if normalized_builder_value != builder_value:
            answers["food_preferences"] = normalized_builder_value
            progress.answers_json = answers
            progress.save(update_fields=["answers_json", "updated_at"])
            builder_value = normalized_builder_value
        return ok(
            {
                "food_preferences": {
                    "builder_value": builder_value,
                    "meal_schedule_days": (progress.answers_json or {}).get("meal_schedule", {}).get("days", {}),
                    "protein_shake": (progress.answers_json or {}).get(
                        "protein_shake",
                        {"enabled": False, "counts_as_meal": True},
                    ),
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
    normalized_shake, _ = _normalize_questionnaire_answer("protein_shake", answers.get("protein_shake"), answers)
    answers["protein_shake"] = normalized_shake
    builder_value = _normalize_food_preference_builder(builder_value, answers=answers)
    results = build_questionnaire_results(
        BuildResultsContext(
            answers=progress.answers_json or {},
            admin_identity=profile.associated_admin if profile else None,
        )
    )
    builder_value = _apply_combo_shape_policy_to_food_preferences(builder_value, results, answers=answers)

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

    was_completed = progress.status == "completed"
    if was_completed and step_key in QUESTIONNAIRE_IMMUTABLE_AFTER_COMPLETION:
        return error(
            "IMMUTABLE_QUESTIONNAIRE_FIELD",
            f"`{step_key}` cannot be edited after onboarding is complete.",
            http_status=400,
        )

    answers = dict(progress.answers_json or {})
    normalized_answer, normalize_error = _normalize_questionnaire_answer(step_key, answer, answers)
    if normalize_error:
        return error(
            "INVALID_STEP_ANSWER",
            "The provided answer is invalid for this questionnaire step.",
            http_status=400,
            details={"step_key": step_key, **normalize_error},
        )
    previous_value = answers.get(step_key)
    answers[step_key] = normalized_answer
    if step_key in {"meal_schedule", "training_schedule"} and "protein_shake" in answers:
        answers["protein_shake"], _ = _normalize_questionnaire_answer("protein_shake", answers.get("protein_shake"), answers)
    inputs_changed = previous_value != normalized_answer

    food_preferences_removed = False
    if (
        was_completed
        and inputs_changed
        and step_key in {"meal_plan_type", "workout_days", "meal_schedule", "training_schedule", "protein_shake"}
    ):
        previous_food_preferences = answers.get("food_preferences")
        if isinstance(previous_food_preferences, dict) and previous_food_preferences:
            del answers["food_preferences"]
            food_preferences_removed = True
        deleted_count, _ = ClientMealComboSelection.objects.filter(user=request.user).delete()
        if deleted_count > 0:
            food_preferences_removed = True

    progress.answers_json = answers
    progress.status = "completed" if was_completed else "in_progress"
    progress.current_step = next_step if next_step in QUESTIONNAIRE_STEPS else step_key
    progress.save(update_fields=["answers_json", "status", "current_step", "updated_at"])
    profile = ClientProfile.objects.filter(user=request.user).select_related("associated_admin").first()
    requires_regen = bool(was_completed and inputs_changed and step_key in QUESTIONNAIRE_REQUIRES_REGEN_FIELDS)
    payload = {
        "message": "Draft saved." if not was_completed else "Questionnaire update saved.",
        "questionnaire": _questionnaire_payload(progress),
        "updates": {
            "was_completed": was_completed,
            "inputs_changed": inputs_changed,
            "requires_meal_plan_regeneration": requires_regen,
            "food_preferences_reset": food_preferences_removed,
        },
    }
    if progress.status == "completed":
        payload["results"] = build_questionnaire_results(
            BuildResultsContext(
                answers=progress.answers_json or {},
                admin_identity=profile.associated_admin if profile else None,
            )
        )
    return ok(payload)


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

    if "protein_shake" not in answers:
        answers["protein_shake"], _ = _normalize_questionnaire_answer("protein_shake", None, answers)
        progress.answers_json = answers
    else:
        normalized_shake, normalize_error = _normalize_questionnaire_answer("protein_shake", answers.get("protein_shake"), answers)
        if normalize_error:
            return error(
                "INVALID_STEP_ANSWER",
                "The provided answer is invalid for this questionnaire step.",
                http_status=400,
                details={"step_key": "protein_shake", **normalize_error},
            )
        answers["protein_shake"] = normalized_shake
        progress.answers_json = answers
    missing = [step for step in _required_questionnaire_steps() if step not in answers or answers.get(step) in (None, "", [])]
    if missing:
        return error(
            "MISSING_REQUIRED_STEPS",
            "Questionnaire is incomplete.",
            http_status=400,
            details={"missing_steps": missing},
        )

    already_completed = progress.status == "completed"
    progress.status = "completed"
    progress.current_step = QUESTIONNAIRE_STEPS[-1]
    progress.completed_at = progress.completed_at or timezone.now()
    progress.save(update_fields=["answers_json", "status", "current_step", "completed_at", "updated_at"])
    profile = ClientProfile.objects.filter(user=request.user).select_related("associated_admin").first()
    return ok(
        {
            "message": "Questionnaire submitted." if not already_completed else "Questionnaire updates saved.",
            "questionnaire": _questionnaire_payload(progress),
            "onboarding": _onboarding_payload(profile, progress),
            "results": build_questionnaire_results(
                BuildResultsContext(
                    answers=progress.answers_json or {},
                    admin_identity=profile.associated_admin if profile else None,
                )
            ),
        }
    )
