from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from django.db import transaction

from core.models import FoodLibraryItem, MealComboTemplate
from users.client_area.models import (
    ClientMealComboSelection,
    ClientMealPlanGeneratedMeal,
    ClientMealPlanGenerationStep1Row,
)


ZERO = Decimal("0")
HUNDRED = Decimal("100")
OZ_TO_GRAMS = Decimal("28.3495")


def _d(value: Any) -> Decimal:
    if value is None:
        return ZERO
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception:
        return ZERO


def _nonnegative(value: Decimal) -> Decimal:
    return value if value > ZERO else ZERO


def _safe_div(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator <= ZERO:
        return ZERO
    try:
        return numerator / denominator
    except Exception:
        return ZERO


def _norm_food_name(value: str | None) -> str:
    return (value or "").strip()


def _food_key(value: str | None) -> str:
    return _norm_food_name(value).lower()


@dataclass
class FullPipelineRunResult:
    generated_meal_count: int
    selected_candidate_count: int
    step1_row_count: int
    note: str


def _slot_definitions(combo: MealComboTemplate) -> dict[str, dict[str, Any]]:
    return {
        "protein1": {"name": combo.protein_slot_1, "split": _d(combo.protein_split_1), "driver_macro": "protein"},
        "protein2": {"name": combo.protein_slot_2, "split": _d(combo.protein_split_2), "driver_macro": "protein"},
        "carbs1": {"name": combo.carb_slot_1, "split": _d(combo.carb_split_1), "driver_macro": "carbs"},
        "carbs2": {"name": combo.carb_slot_2, "split": _d(combo.carb_split_2), "driver_macro": "carbs"},
        "fats1": {"name": combo.fat_slot_1, "split": _d(combo.fat_split_1), "driver_macro": "fats"},
        "fats2": {"name": combo.fat_slot_2, "split": _d(combo.fat_split_2), "driver_macro": "fats"},
    }


def _food_macros_by_name(names: list[str]) -> dict[str, FoodLibraryItem]:
    normalized = sorted({_food_key(name) for name in names if _norm_food_name(name) and _norm_food_name(name) != "-"})
    if not normalized:
        return {}
    rows = FoodLibraryItem.objects.all().order_by("source_food_id")
    by_name: dict[str, FoodLibraryItem] = {}
    for row in rows:
        key = _food_key(row.name)
        if key in normalized and key not in by_name:
            by_name[key] = row
    return by_name


def _macro_density(food: FoodLibraryItem | None, macro: str) -> Decimal:
    if not food:
        return ZERO
    return _nonnegative(_d(getattr(food, macro, ZERO)))


def _step3_amount(slot_negative: Decimal, slot_food: FoodLibraryItem | None, driver_macro: str) -> Decimal:
    # Step3 parity: convert macro deficit to food amount by dividing by the slot's primary macro density.
    return _safe_div(_nonnegative(slot_negative), _macro_density(slot_food, driver_macro))


def _slot_macro_contrib(amount: Decimal, slot_food: FoodLibraryItem | None, macro: str) -> Decimal:
    return _nonnegative(amount) * _macro_density(slot_food, macro)


def _meal_targets_from_day_payload(day_payload: dict[str, Any]) -> dict[int, dict[str, Decimal]]:
    targets: dict[int, dict[str, Decimal]] = {}
    for row in list(day_payload.get("meal_macro_splits") or []):
        meal_number = int((row or {}).get("meal_number") or 0)
        if meal_number < 1:
            continue
        grams = (row or {}).get("grams") or {}
        targets[meal_number] = {
            "protein": _nonnegative(_d(grams.get("protein_g"))),
            "carbs": _nonnegative(_d(grams.get("carbs_g"))),
            "fats": _nonnegative(_d(grams.get("fats_g"))),
        }
    return targets


def _evaluate_candidate(step1_row, combo: MealComboTemplate, foods_by_name: dict[str, FoodLibraryItem], targets: dict[str, Decimal]):
    # Step2
    slot_defs = _slot_definitions(combo)
    slot_negatives = {
        "protein1": _nonnegative(_d(step1_row.pro_negative) * slot_defs["protein1"]["split"]),
        "protein2": _nonnegative(_d(step1_row.pro_negative) * slot_defs["protein2"]["split"]),
        "carbs1": _nonnegative(_d(step1_row.carbs_negative) * slot_defs["carbs1"]["split"]),
        "carbs2": _nonnegative(_d(step1_row.carbs_negative) * slot_defs["carbs2"]["split"]),
        "fats1": _nonnegative(_d(step1_row.fats_negative) * slot_defs["fats1"]["split"]),
        "fats2": _nonnegative(_d(step1_row.fats_negative) * slot_defs["fats2"]["split"]),
    }

    # Step3 (food amounts, same shape as final Step10 payload)
    amounts = {}
    for slot_key, slot_cfg in slot_defs.items():
        food = foods_by_name.get(_food_key(slot_cfg["name"]))
        amounts[slot_key] = _step3_amount(slot_negatives[slot_key], food, slot_cfg["driver_macro"])

    # Step4 + Step5 (macro recomposition and aggregation)
    complete = {"protein": ZERO, "carbs": ZERO, "fats": ZERO}
    for slot_key, slot_cfg in slot_defs.items():
        food = foods_by_name.get(_food_key(slot_cfg["name"]))
        amt = amounts[slot_key]
        complete["protein"] += _slot_macro_contrib(amt, food, "protein")
        complete["carbs"] += _slot_macro_contrib(amt, food, "carbs")
        complete["fats"] += _slot_macro_contrib(amt, food, "fats")

    # Step6, Step7, Step8
    residual_pro = targets["protein"] - complete["protein"]
    residual_carbs = targets["carbs"] - complete["carbs"]
    residual_fats = targets["fats"] - complete["fats"]
    error_est = abs(residual_pro) + abs(residual_carbs) + abs(residual_fats)

    return {
        "error_code": int(step1_row.error_code),
        "error_est": error_est,
        "amounts": amounts,
    }


@transaction.atomic
def run_steps_2_to_10_for_day(*, job, day_payload: dict[str, Any]) -> FullPipelineRunResult:
    """
    Port of WP Steps 2-10 collapsed into one deterministic server-side pass:
    - preserves Step2..Step9 formulas
    - writes Step10-equivalent rows into ClientMealPlanGeneratedMeal
    """
    day = job.day_of_week
    user = job.user

    step1_rows_qs = ClientMealPlanGenerationStep1Row.objects.filter(job=job).order_by("meal_number", "error_code")
    step1_row_count = step1_rows_qs.count()
    if step1_row_count == 0:
        raise ValueError("Step1 rows are missing for this job.")

    combo_rows = (
        ClientMealComboSelection.objects.filter(user=user, day_of_week=day)
        .select_related("combo_template")
        .order_by("meal_number")
    )
    combo_by_meal = {int(row.meal_number): row.combo_template for row in combo_rows}
    if not combo_by_meal:
        raise ValueError(f"No saved meal combo selections found for {day}.")

    targets_by_meal = _meal_targets_from_day_payload(day_payload)
    if not targets_by_meal:
        raise ValueError(f"No meal macro targets found for {day}.")

    missing_combo_meals = sorted(set(targets_by_meal.keys()) - set(combo_by_meal.keys()))
    if missing_combo_meals:
        raise ValueError(f"Missing combo selections for meals: {missing_combo_meals}.")

    referenced_food_names: list[str] = []
    for combo in combo_by_meal.values():
        referenced_food_names.extend(
            [
                combo.protein_slot_1,
                combo.protein_slot_2,
                combo.carb_slot_1,
                combo.carb_slot_2,
                combo.fat_slot_1,
                combo.fat_slot_2,
            ]
        )
    foods_by_name = _food_macros_by_name(referenced_food_names)

    winners_by_meal: dict[int, dict[str, Any]] = {}
    for row in step1_rows_qs.iterator(chunk_size=5000):
        meal_number = int(row.meal_number)
        combo = combo_by_meal.get(meal_number)
        target = targets_by_meal.get(meal_number)
        if not combo or not target:
            continue
        candidate = _evaluate_candidate(row, combo, foods_by_name, target)
        current = winners_by_meal.get(meal_number)
        if not current:
            winners_by_meal[meal_number] = candidate
            continue
        if (candidate["error_est"], candidate["error_code"]) < (current["error_est"], current["error_code"]):
            winners_by_meal[meal_number] = candidate

    if not winners_by_meal:
        raise ValueError("No generation candidates could be evaluated for selected combos.")

    # Step10 materialization
    ClientMealPlanGeneratedMeal.objects.filter(job=job).delete()
    final_rows = []
    for meal_number in sorted(winners_by_meal.keys()):
        combo = combo_by_meal[meal_number]
        winner = winners_by_meal[meal_number]
        amounts = winner["amounts"]
        final_rows.append(
            ClientMealPlanGeneratedMeal(
                job=job,
                user=user,
                day_of_week=day,
                meal_number=meal_number,
                combo_template=combo,
                error_code=int(winner["error_code"]),
                protein1_total=amounts["protein1"],
                protein2_total=amounts["protein2"],
                carbs1_total=amounts["carbs1"],
                carbs2_total=amounts["carbs2"],
                fats1_total=amounts["fats1"],
                fats2_total=amounts["fats2"],
            )
        )

    ClientMealPlanGeneratedMeal.objects.bulk_create(
        final_rows,
        batch_size=500,
        update_conflicts=True,
        unique_fields=["job", "day_of_week", "meal_number"],
        update_fields=[
            "combo_template",
            "error_code",
            "protein1_total",
            "protein2_total",
            "carbs1_total",
            "carbs2_total",
            "fats1_total",
            "fats2_total",
            "updated_at",
        ],
    )

    return FullPipelineRunResult(
        generated_meal_count=len(final_rows),
        selected_candidate_count=len(winners_by_meal),
        step1_row_count=step1_row_count,
        note="WP Steps 2-10 ported into a collapsed Python pipeline (same scoring + winner selection).",
    )

