from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from core.seed_data.admin_parameter_defaults import get_admin_parameter_defaults_v1


WEEK_DAYS = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]


def _to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _clamp_nonnegative(value: float) -> float:
    return value if value > 0 else 0.0


def _parse_date(value: str | None):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _calculate_age_from_dob(dob_iso: str | None):
    dob = _parse_date(dob_iso)
    if not dob:
        return None
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def _normalize_height_cm(height_answer: Any):
    if isinstance(height_answer, (int, float)):
        cm = _to_float(height_answer)
        return cm if cm > 0 else None
    if isinstance(height_answer, str) and height_answer.strip() != "":
        cm = _to_float(height_answer)
        return cm if cm > 0 else None
    if not isinstance(height_answer, dict):
        return None
    unit = (height_answer.get("unit") or "imperial").lower()
    if unit == "cm":
        cm = _to_float(height_answer.get("cm"))
        return cm if cm > 0 else None
    feet = _to_float(height_answer.get("feet"))
    inches = _to_float(height_answer.get("inches"))
    if feet <= 0 and inches < 0:
        return None
    cm = (feet * 30.48) + (inches * 2.54)
    return cm if cm > 0 else None


def _normalize_weight(weight_answer: dict[str, Any] | None):
    if not isinstance(weight_answer, dict):
        return None, None
    unit = (weight_answer.get("unit") or "lbs").lower()
    value = _to_float(weight_answer.get("value"))
    if value <= 0:
        return None, None
    if unit == "kg":
        return value, value * 2.20462
    return value * 0.453592, value


def _calculate_bmr(gender: str | None, weight_kg: float, height_cm: float, age: int):
    g = (gender or "").strip().lower()
    if g == "male":
        return (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
    return (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 160


def _safe_get_admin_params(admin_identity):
    settings = getattr(admin_identity, "parameter_settings", None) if admin_identity else None
    if settings and getattr(settings, "parameters_json", None):
        return settings.parameters_json
    return get_admin_parameter_defaults_v1()


def _admin_param_source(admin_identity):
    settings = getattr(admin_identity, "parameter_settings", None) if admin_identity else None
    if settings and getattr(settings, "parameters_json", None):
        return "associated_admin"
    return "dta_default_v1"


def _get_goal_adjustment_percent(params: dict[str, Any], goal: str):
    mapping = {
        "lose": "lose_weight_percent",
        "maintain": "maintain_weight_percent",
        "gain": "gain_weight_percent",
    }
    key = mapping.get(goal or "")
    return _to_float(((params.get("goal_calorie_adjustments") or {}).get(key)), 0.0) if key else 0.0


def _get_weekly_tdee_table(params: dict[str, Any], lifestyle: str, training_days_per_week: int):
    tdee = params.get("tdee") or {}
    weekly = tdee.get("weekly_day_multiplier_splits") or {}
    lifestyle_payload = weekly.get(lifestyle) or {}
    tables = lifestyle_payload.get("tables_by_training_days_per_week") or {}
    return tables.get(str(training_days_per_week)) or {}


def _partition_day_multipliers_for_schedule(day_multipliers: list[float], workout_days: list[str]):
    selected_workout = [d for d in WEEK_DAYS if d in set(workout_days or [])]
    off_days = [d for d in WEEK_DAYS if d not in set(selected_workout)]
    if len(day_multipliers) != 7:
        day_multipliers = [1.2] * 7

    sorted_desc = sorted([_to_float(v, 1.2) for v in day_multipliers], reverse=True)
    workout_count = len(selected_workout)
    workout_pool = sorted_desc[:workout_count]
    off_pool = sorted_desc[workout_count:]

    assigned = {}
    for idx, day in enumerate(selected_workout):
        assigned[day] = workout_pool[idx] if idx < len(workout_pool) else (workout_pool[-1] if workout_pool else 1.2)
    for idx, day in enumerate(off_days):
        assigned[day] = off_pool[idx] if idx < len(off_pool) else (off_pool[-1] if off_pool else 1.2)
    return assigned


def _select_macro_rules_for_day(params, meal_plan_type, goal, is_workout_day):
    meal_plans = params.get("meal_plans") or {}
    mpt = meal_plans.get(meal_plan_type) or {}
    if meal_plan_type == "carb_cycling":
        rules_by_goal = mpt.get("macro_rules_by_goal") or {}
        goal_rules = rules_by_goal.get(goal) or {}
        carb_key = "high_day" if is_workout_day else "low_day"
        carb_set = goal_rules.get(carb_key) or {}
        return {
            "protein_factor_value": _to_float(goal_rules.get("protein_factor_value"), 1.0),
            "carb_percent": _to_float(carb_set.get("carb_percent"), 0.0),
            "fat_percent": _to_float(carb_set.get("fat_percent"), 0.0),
            "carb_cycling_mode": "high_carbs" if is_workout_day else "low_carbs",
        }

    rules_by_goal = mpt.get("macro_rules_by_goal") or {}
    goal_rules = rules_by_goal.get(goal) or {}
    return {
        "protein_factor_value": _to_float(goal_rules.get("protein_factor_value"), 1.0),
        "carb_percent": _to_float(goal_rules.get("carb_percent"), 0.0),
        "fat_percent": _to_float(goal_rules.get("fat_percent"), 0.0),
        "carb_cycling_mode": None,
    }


def _calculate_daily_macros(calories: float, weight_lbs: float, macro_rules: dict[str, Any]):
    protein_g = _clamp_nonnegative(weight_lbs * _to_float(macro_rules.get("protein_factor_value"), 1.0))
    protein_calories = protein_g * 4
    remaining_calories = max(0.0, calories - protein_calories)
    carb_percent = _to_float(macro_rules.get("carb_percent"), 0.0)
    fat_percent = _to_float(macro_rules.get("fat_percent"), 0.0)
    carbs_g = (remaining_calories * (carb_percent / 100.0)) / 4.0
    fats_g = (remaining_calories * (fat_percent / 100.0)) / 9.0
    return {
        "protein_g": round(protein_g, 2),
        "carbs_g": round(_clamp_nonnegative(carbs_g), 2),
        "fats_g": round(_clamp_nonnegative(fats_g), 2),
        "macro_rules": {
            "protein_factor_value": round(_to_float(macro_rules.get("protein_factor_value"), 1.0), 4),
            "carb_percent": round(carb_percent, 3),
            "fat_percent": round(fat_percent, 3),
        },
    }


def _get_distribution_table(params, meal_plan_type, meals_per_day, training_schedule_value, carb_cycling_mode=None):
    meal_plans = params.get("meal_plans") or {}
    plan_payload = meal_plans.get(meal_plan_type) or {}
    distributions = plan_payload.get("meal_macro_distribution") or {}

    if meal_plan_type == "carb_cycling":
        bucket = distributions.get(f"meals_{meals_per_day}") or {}
        scenario_tables = bucket.get(carb_cycling_mode or "low_carbs") or {}
    else:
        scenario_tables = distributions.get(f"meals_{meals_per_day}") or {}

    scenario_key = str(training_schedule_value or "no_training").strip()
    if scenario_key.startswith("before_meal_"):
        scenario_key = f"train_{scenario_key}"
    return scenario_tables.get(scenario_key) or scenario_tables.get("no_training") or {}


def _build_meal_splits_for_day(distribution_table, daily_macros):
    rows = []
    for meal_key in sorted(distribution_table.keys(), key=lambda k: int(k.split("_")[-1])):
        pct = distribution_table.get(meal_key) or {}
        rows.append(
            {
                "meal_key": meal_key,
                "meal_number": int(meal_key.split("_")[-1]),
                "percentages": {
                    "protein": round(_to_float(pct.get("protein"), 0.0), 3),
                    "carbs": round(_to_float(pct.get("carbs"), 0.0), 3),
                    "fats": round(_to_float(pct.get("fats"), 0.0), 3),
                },
                "grams": {
                    "protein_g": round(daily_macros["protein_g"] * (_to_float(pct.get("protein"), 0.0) / 100.0), 2),
                    "carbs_g": round(daily_macros["carbs_g"] * (_to_float(pct.get("carbs"), 0.0) / 100.0), 2),
                    "fats_g": round(daily_macros["fats_g"] * (_to_float(pct.get("fats"), 0.0) / 100.0), 2),
                },
            }
        )
    return rows


@dataclass
class BuildResultsContext:
    answers: dict[str, Any]
    admin_identity: Any = None


def build_questionnaire_results(context: BuildResultsContext):
    answers = context.answers or {}
    required_core = [
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
    for key in required_core:
        if key not in answers:
            return None

    age = _calculate_age_from_dob(answers.get("date_of_birth"))
    height_cm = _normalize_height_cm(answers.get("height"))
    weight_kg, weight_lbs = _normalize_weight(answers.get("weight"))
    if age is None or not height_cm or not weight_kg or not weight_lbs:
        return None

    gender = (answers.get("gender") or "").strip().lower()
    goal = (answers.get("goal") or "").strip().lower()
    lifestyle = (answers.get("lifestyle") or "").strip().lower()
    meal_plan_type = (answers.get("meal_plan_type") or "").strip().lower()
    workout_days = [d for d in WEEK_DAYS if d in set(answers.get("workout_days") or [])]
    meal_schedule = (answers.get("meal_schedule") or {}).get("days") or {}
    training_schedule = answers.get("training_schedule") or {}
    training_days_per_week = len(workout_days)

    params = _safe_get_admin_params(context.admin_identity)
    admin_param_source = _admin_param_source(context.admin_identity)
    bmr = _calculate_bmr(gender, weight_kg, height_cm, age)
    goal_pct = _get_goal_adjustment_percent(params, goal)

    tdee_table = _get_weekly_tdee_table(params, lifestyle, training_days_per_week)
    day_multipliers = tdee_table.get("day_multipliers") or [1.2] * 7
    assigned_multipliers = _partition_day_multipliers_for_schedule(day_multipliers, workout_days)

    category_multipliers = ((params.get("tdee") or {}).get("category_multipliers") or {})
    selected_category = tdee_table.get("category")
    target_category_multiplier = _to_float(category_multipliers.get(str(selected_category)), 0.0) if selected_category else 0.0

    weekly_rows = []
    for day in WEEK_DAYS:
        is_workout_day = day in workout_days
        meals_per_day = int(meal_schedule.get(day) or 0)
        if meals_per_day not in (3, 4, 5, 6):
            meals_per_day = 3
        training_value = training_schedule.get(day) if is_workout_day else "no_training"
        if not training_value and is_workout_day:
            training_value = "no_training"

        day_multiplier = _to_float(assigned_multipliers.get(day), 1.2)
        tdee_calories = bmr * day_multiplier
        adjusted_calories = tdee_calories * (1 + (goal_pct / 100.0))

        macro_rules = _select_macro_rules_for_day(params, meal_plan_type, goal, is_workout_day)
        daily_macros = _calculate_daily_macros(adjusted_calories, weight_lbs, macro_rules)
        distribution_table = _get_distribution_table(
            params,
            meal_plan_type,
            meals_per_day,
            training_value if training_value in {"no_training"} or str(training_value).startswith("before_meal_") else "no_training",
            carb_cycling_mode=macro_rules.get("carb_cycling_mode"),
        )
        meal_splits = _build_meal_splits_for_day(distribution_table, daily_macros)

        weekly_rows.append(
            {
                "day": day,
                "is_workout_day": is_workout_day,
                "training_before_meal": None if not is_workout_day or training_value == "no_training" else training_value,
                "meals_per_day": meals_per_day,
                "tdee_multiplier": round(day_multiplier, 6),
                "tdee_calories": round(tdee_calories, 2),
                "calories_target": round(adjusted_calories, 2),
                "daily_macros": daily_macros,
                "meal_macro_splits": meal_splits,
                "carb_cycling_mode": macro_rules.get("carb_cycling_mode"),
            }
        )

    workout_rows = [r for r in weekly_rows if r["is_workout_day"]]
    off_rows = [r for r in weekly_rows if not r["is_workout_day"]]
    avg = lambda rows, key: round(sum(r[key] for r in rows) / len(rows), 2) if rows else None

    return {
        "profile": {
            "gender": gender,
            "age": age,
            "height_cm": round(height_cm, 2),
            "weight_kg": round(weight_kg, 2),
            "weight_lbs": round(weight_lbs, 2),
            "goal": goal,
            "lifestyle": lifestyle,
            "meal_plan_type": meal_plan_type,
            "training_days_per_week": training_days_per_week,
        },
        "core_calculations": {
            "bmr": round(bmr, 2),
            "goal_calorie_adjustment_percent": round(goal_pct, 2),
            "tdee_category": selected_category,
            "tdee_category_target_multiplier": round(target_category_multiplier, 6) if target_category_multiplier else None,
            "weekly_average_multiplier": round(sum(r["tdee_multiplier"] for r in weekly_rows) / len(weekly_rows), 6) if weekly_rows else None,
        },
        "parameter_settings": {
            "source": admin_param_source,
            "defaults_version": (params or {}).get("version") or "v1",
        },
        "summary": {
            "workout_day_avg_calories": avg(workout_rows, "calories_target"),
            "off_day_avg_calories": avg(off_rows, "calories_target"),
            "workout_day_avg_tdee": avg(workout_rows, "tdee_calories"),
            "off_day_avg_tdee": avg(off_rows, "tdee_calories"),
        },
        "weekly_days": weekly_rows,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }
