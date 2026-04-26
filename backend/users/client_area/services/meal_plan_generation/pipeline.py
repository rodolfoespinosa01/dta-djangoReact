from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import logging
from typing import Any

from django.db import transaction

from core.models import FoodLibraryItem, MealComboTemplate
from core.services.meal_combo_shape_policy import select_meal_combo_template_for_target
from users.client_area.models import (
    ClientFoodOverride,
    ClientMealComboSelection,
    ClientMealPlanGeneratedMeal,
    ClientMealPlanGenerationStep1Row,
)

logger = logging.getLogger(__name__)


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


def _has_usable_macro_data(row: FoodLibraryItem) -> bool:
    return any(_d(getattr(row, macro, ZERO)) > ZERO for macro in ("protein", "carbs", "fats"))


@dataclass
class FullPipelineRunResult:
    generated_meal_count: int
    selected_candidate_count: int
    step1_row_count: int
    note: str


def _selected_foods_by_meal_from_snapshot(job) -> dict[int, dict[str, str]]:
    snapshot = job.input_snapshot_json or {}
    raw = snapshot.get("day_selected_slot_foods")
    if not isinstance(raw, dict):
        return {}

    output: dict[int, dict[str, str]] = {}
    for meal_key, slot_map in raw.items():
        try:
            meal_number = int(meal_key)
        except (TypeError, ValueError):
            continue
        if meal_number < 1 or not isinstance(slot_map, dict):
            continue

        normalized = {}
        for slot_key in ("protein_1", "protein_2", "carbs_1", "carbs_2", "fats_1", "fats_2"):
            value = _norm_food_name(slot_map.get(slot_key))
            if value:
                normalized[slot_key] = value
        if normalized:
            output[meal_number] = normalized

    return output


def _slot_definitions(combo: MealComboTemplate) -> dict[str, dict[str, Any]]:
    return {
        "protein1": {
            "category_name": combo.protein_slot_1,
            "selected_key": "protein_1",
            "split": _d(combo.protein_split_1),
            "driver_macro": "protein",
        },
        "protein2": {
            "category_name": combo.protein_slot_2,
            "selected_key": "protein_2",
            "split": _d(combo.protein_split_2),
            "driver_macro": "protein",
        },
        "carbs1": {
            "category_name": combo.carb_slot_1,
            "selected_key": "carbs_1",
            "split": _d(combo.carb_split_1),
            "driver_macro": "carbs",
        },
        "carbs2": {
            "category_name": combo.carb_slot_2,
            "selected_key": "carbs_2",
            "split": _d(combo.carb_split_2),
            "driver_macro": "carbs",
        },
        "fats1": {
            "category_name": combo.fat_slot_1,
            "selected_key": "fats_1",
            "split": _d(combo.fat_split_1),
            "driver_macro": "fats",
        },
        "fats2": {
            "category_name": combo.fat_slot_2,
            "selected_key": "fats_2",
            "split": _d(combo.fat_split_2),
            "driver_macro": "fats",
        },
    }


def _food_macros_by_name(names: list[str]) -> dict[str, Any]:
    normalized = sorted({_food_key(name) for name in names if _norm_food_name(name) and _norm_food_name(name) != "-"})
    if not normalized:
        return {}
    rows = list(
        FoodLibraryItem.objects.filter(
            is_active=True,
            approval_status=FoodLibraryItem.ApprovalStatus.APPROVED,
        ).order_by("is_placeholder", "-is_standard", "source_food_id")
    )
    by_name: dict[str, FoodLibraryItem] = {}

    # 1) Direct canonical/display-name matches take priority. Some canonical combo foods
    # are marked as placeholder/category-reference rows, but still carry the
    # macro data needed for serving calculations.
    for row in rows:
        if _food_key(row.name) == "-" or not _has_usable_macro_data(row):
            continue
        for raw_key in (row.name, row.display_name, row.canonical_name, row.canonical_category):
            key = _food_key(raw_key)
            if key in normalized and key not in by_name:
                by_name[key] = row

    # 2) Backward compatibility: category tokens (combo slot values) map to
    # the first approved standard food found for that category.
    unresolved = {key for key in normalized if key not in by_name}
    if unresolved:
        for row in rows:
            if _food_key(row.category) == "-" or not _has_usable_macro_data(row):
                continue
            for raw_key in (row.category, row.canonical_category):
                category_key = _food_key(raw_key)
                if category_key in unresolved and category_key not in by_name:
                    by_name[category_key] = row

    return by_name


def _food_overrides_by_name(user, names: list[str]) -> dict[str, ClientFoodOverride]:
    normalized_names = {
        _norm_food_name(name)
        for name in names
        if _norm_food_name(name) and _norm_food_name(name) != "-"
    }
    if not normalized_names:
        return {}
    rows = ClientFoodOverride.objects.filter(
        user=user,
        active=True,
        canonical_category__in=normalized_names,
    )
    return {_food_key(row.canonical_category): row for row in rows}


def _macro_density(food: Any | None, macro: str) -> Decimal:
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


def _training_adjacent_meals(day_payload: dict[str, Any]) -> set[int]:
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


def _evaluate_candidate(
    step1_row,
    combo: MealComboTemplate,
    foods_by_name: dict[str, FoodLibraryItem],
    targets: dict[str, Decimal],
    selected_foods_for_meal: dict[str, str] | None = None,
):
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
        selected_name = _norm_food_name((selected_foods_for_meal or {}).get(slot_cfg["selected_key"]))
        effective_name = selected_name or _norm_food_name(slot_cfg["category_name"])
        food = foods_by_name.get(_food_key(effective_name))
        amounts[slot_key] = _step3_amount(slot_negatives[slot_key], food, slot_cfg["driver_macro"])

    # Step4 + Step5 (macro recomposition and aggregation)
    complete = {"protein": ZERO, "carbs": ZERO, "fats": ZERO}
    for slot_key, slot_cfg in slot_defs.items():
        selected_name = _norm_food_name((selected_foods_for_meal or {}).get(slot_cfg["selected_key"]))
        effective_name = selected_name or _norm_food_name(slot_cfg["category_name"])
        food = foods_by_name.get(_food_key(effective_name))
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
        "step1_row": step1_row,
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

    selected_foods_by_meal = _selected_foods_by_meal_from_snapshot(job)
    training_adjacent_meals = _training_adjacent_meals(day_payload)

    missing_combo_meals = sorted(set(targets_by_meal.keys()) - set(combo_by_meal.keys()))
    if missing_combo_meals:
        raise ValueError(f"Missing combo selections for meals: {missing_combo_meals}.")

    selected_combo_by_meal: dict[int, MealComboTemplate] = {}
    combo_debug_by_meal: dict[int, dict[str, Any]] = {}
    for meal_number, saved_combo in combo_by_meal.items():
        target = targets_by_meal.get(meal_number)
        if not target:
            selected_combo_by_meal[meal_number] = saved_combo
            continue
        decision = select_meal_combo_template_for_target(
            saved_combo=saved_combo,
            meal_target=target,
            is_training_adjacent=meal_number in training_adjacent_meals,
            selected_slots=selected_foods_by_meal.get(meal_number),
        )
        selected_combo_by_meal[meal_number] = decision.combo
        combo_debug_by_meal[meal_number] = {
            "protein_target": target["protein"],
            "carb_target": target["carbs"],
            "is_training_adjacent": meal_number in training_adjacent_meals,
            "preferred_protein_structure": decision.preferred_shape.protein_structure,
            "preferred_carb_structure": decision.preferred_shape.carb_structure,
            "candidate_count_before_filtering": decision.candidate_count_before_filtering,
            "candidate_count_after_filtering": decision.candidate_count_after_filtering,
            "chosen_combo_id": decision.combo.combo_id,
            "fallback_reason": decision.fallback_reason,
        }
        logger.info(
            "Meal combo shape selection: meal=%s protein_target=%s carb_target=%s "
            "training_adjacent=%s preferred_protein=%s preferred_carb=%s "
            "candidates_before=%s candidates_after=%s chosen_combo_id=%s fallback_reason=%s",
            meal_number,
            target["protein"],
            target["carbs"],
            meal_number in training_adjacent_meals,
            decision.preferred_shape.protein_structure,
            decision.preferred_shape.carb_structure,
            decision.candidate_count_before_filtering,
            decision.candidate_count_after_filtering,
            decision.combo.combo_id,
            decision.fallback_reason,
        )
    combo_by_meal = selected_combo_by_meal

    referenced_food_names: list[str] = []
    for meal_number, combo in combo_by_meal.items():
        selected_slot_foods = selected_foods_by_meal.get(meal_number) or {}
        referenced_food_names.extend(list(selected_slot_foods.values()))
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
    override_foods_by_name = _food_overrides_by_name(user, referenced_food_names)
    effective_foods_by_name = {**foods_by_name, **override_foods_by_name}

    winners_by_meal: dict[int, dict[str, Any]] = {}
    for row in step1_rows_qs.iterator(chunk_size=5000):
        meal_number = int(row.meal_number)
        combo = combo_by_meal.get(meal_number)
        target = targets_by_meal.get(meal_number)
        if not combo or not target:
            continue
        candidate = _evaluate_candidate(
            row,
            combo,
            foods_by_name,
            target,
            selected_foods_for_meal=selected_foods_by_meal.get(meal_number),
        )
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
        if override_foods_by_name:
            amounts = _evaluate_candidate(
                winner["step1_row"],
                combo,
                effective_foods_by_name,
                targets_by_meal[meal_number],
                selected_foods_for_meal=selected_foods_by_meal.get(meal_number),
            )["amounts"]
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

    if combo_debug_by_meal:
        snapshot = dict(job.input_snapshot_json or {})
        snapshot["meal_combo_shape_debug"] = {
            str(meal_number): {
                **debug,
                "protein_target": str(debug["protein_target"]),
                "carb_target": str(debug["carb_target"]),
            }
            for meal_number, debug in sorted(combo_debug_by_meal.items())
        }
        job.input_snapshot_json = snapshot
        job.save(update_fields=["input_snapshot_json", "updated_at"])

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
