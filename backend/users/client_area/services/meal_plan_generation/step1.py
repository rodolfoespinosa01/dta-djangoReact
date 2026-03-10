from __future__ import annotations

from typing import Any

from core.models import ComboMacroErrorLookup

from users.client_area.models import ClientMealPlanGenerationStep1Row


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def build_step1_rows_for_day(job, day_payload: dict[str, Any], chunk_size: int = 5000) -> int:
    meal_splits = list(day_payload.get("meal_macro_splits") or [])
    if not meal_splits:
        raise ValueError("No meal macro splits available for selected day.")

    error_rows = list(
        ComboMacroErrorLookup.objects.values("error_code", "protein_error", "carbs_error", "fats_error").order_by("error_code")
    )
    if not error_rows:
        raise ValueError("Combo macro error lookup table is empty.")

    ClientMealPlanGenerationStep1Row.objects.filter(job=job).delete()

    pending = []
    total_created = 0

    for meal in meal_splits:
        meal_number = int(meal.get("meal_number") or 0)
        grams = meal.get("grams") or {}
        target_protein = max(0.0, _to_float(grams.get("protein_g")))
        target_carbs = max(0.0, _to_float(grams.get("carbs_g")))
        target_fats = max(0.0, _to_float(grams.get("fats_g")))
        if meal_number < 1:
            continue

        for error_row in error_rows:
            pro_negative = max(0.0, target_protein - _to_float(error_row.get("protein_error")))
            carbs_negative = max(0.0, target_carbs - _to_float(error_row.get("carbs_error")))
            fats_negative = max(0.0, target_fats - _to_float(error_row.get("fats_error")))

            pending.append(
                ClientMealPlanGenerationStep1Row(
                    job=job,
                    meal_number=meal_number,
                    error_code=int(error_row["error_code"]),
                    pro_negative=pro_negative,
                    carbs_negative=carbs_negative,
                    fats_negative=fats_negative,
                )
            )

            if len(pending) >= chunk_size:
                ClientMealPlanGenerationStep1Row.objects.bulk_create(
                    pending,
                    batch_size=chunk_size,
                    update_conflicts=True,
                    unique_fields=["job", "meal_number", "error_code"],
                    update_fields=["pro_negative", "carbs_negative", "fats_negative"],
                )
                total_created += len(pending)
                pending = []

    if pending:
        ClientMealPlanGenerationStep1Row.objects.bulk_create(
            pending,
            batch_size=chunk_size,
            update_conflicts=True,
            unique_fields=["job", "meal_number", "error_code"],
            update_fields=["pro_negative", "carbs_negative", "fats_negative"],
        )
        total_created += len(pending)

    return total_created
