from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from django.db.models import QuerySet

from core.models import MealComboTemplate

TWO_PROTEIN_MIN_G = Decimal("50")
ONE_CARB_PREFERRED_BELOW_G = Decimal("45")
TWO_CARB_ALLOWED_G = Decimal("60")
TRAINING_ADJACENT_TWO_CARB_MIN_G = Decimal("45")
SECOND_FAT_MIN_G = Decimal("20")
COOKING_FAT_SLOT = "Oil STANDARD"
LEAN_PROTEIN_COOKING_FAT_REQUIRED = frozenset(
    {
        "Chicken Breast STANDARD",
        "Fish STANDARD",
        "Salmon STANDARD",
        "Tilapia STANDARD",
        "Tuna STANDARD",
        "Cod STANDARD",
        "Catfish STANDARD",
        "Shrimp STANDARD",
        "Merluza, Hake (flesh only) STANDARD",
    }
)


def _normalize_slot(value):
    normalized = str(value or "").strip()
    return normalized or "-"


def _target_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value or "0"))
    except Exception:
        return Decimal("0")


def allows_second_protein(protein_target_g: Any) -> bool:
    return _target_decimal(protein_target_g) >= TWO_PROTEIN_MIN_G


def allows_second_carb(carb_target_g: Any, is_training_adjacent: bool = False) -> bool:
    target = _target_decimal(carb_target_g)
    if target < ONE_CARB_PREFERRED_BELOW_G:
        return False
    if target >= TWO_CARB_ALLOWED_G:
        return True
    return bool(is_training_adjacent) and target >= TRAINING_ADJACENT_TWO_CARB_MIN_G


def allows_second_fat(fat_target_g: Any) -> bool:
    return _target_decimal(fat_target_g) >= SECOND_FAT_MIN_G


def requires_cooking_fat_for_protein(protein_name: Any) -> bool:
    return _normalize_slot(protein_name) in LEAN_PROTEIN_COOKING_FAT_REQUIRED


@dataclass(frozen=True)
class MealComboShapePreference:
    allows_second_protein: bool
    allows_second_carb: bool
    allows_second_fat: bool
    preferred_protein_slot_2: str | None
    preferred_carb_slot_2: str | None
    preferred_fat_slot_2: str | None
    protein_structure: str
    carb_structure: str
    fat_structure: str


@dataclass(frozen=True)
class MealComboSelectionDecision:
    combo: MealComboTemplate
    preferred_shape: MealComboShapePreference
    candidate_count_before_filtering: int
    candidate_count_after_filtering: int
    fallback_reason: str | None = None


def preferred_combo_shape_for_meal(meal_target: dict[str, Any] | None, is_training_adjacent: bool = False):
    target = meal_target or {}
    protein_allows_second = allows_second_protein(target.get("protein"))
    carb_allows_second = allows_second_carb(target.get("carbs"), is_training_adjacent=is_training_adjacent)
    fat_allows_second = allows_second_fat(target.get("fats"))
    return MealComboShapePreference(
        allows_second_protein=protein_allows_second,
        allows_second_carb=carb_allows_second,
        allows_second_fat=fat_allows_second,
        preferred_protein_slot_2=None if protein_allows_second else "-",
        preferred_carb_slot_2=None if carb_allows_second else "-",
        preferred_fat_slot_2=None if fat_allows_second else "-",
        protein_structure="one_or_two_protein" if protein_allows_second else "one_protein",
        carb_structure="one_or_two_carb" if carb_allows_second else "one_carb",
        fat_structure="one_or_two_fat" if fat_allows_second else "one_fat",
    )


def _selected_values_for_group(selected_slots: dict[str, Any] | None, keys: tuple[str, str], saved_values: tuple[Any, Any]):
    selected = selected_slots or {}
    values = {_normalize_slot(selected.get(key)) for key in keys if _normalize_slot(selected.get(key)) != "-"}
    values.update({_normalize_slot(value) for value in saved_values if _normalize_slot(value) != "-"})
    return values


def _compatible_combo_queryset(
    *,
    saved_combo: MealComboTemplate,
    selected_slots: dict[str, Any] | None = None,
    queryset: QuerySet | None = None,
):
    qs = queryset if queryset is not None else MealComboTemplate.objects.all()
    protein_values = _selected_values_for_group(
        selected_slots,
        ("protein_1", "protein_2"),
        (saved_combo.protein_slot_1, saved_combo.protein_slot_2),
    )
    carb_values = _selected_values_for_group(
        selected_slots,
        ("carbs_1", "carbs_2"),
        (saved_combo.carb_slot_1, saved_combo.carb_slot_2),
    )
    fat_values = _selected_values_for_group(
        selected_slots,
        ("fats_1", "fats_2"),
        (saved_combo.fat_slot_1, saved_combo.fat_slot_2),
    )

    if protein_values:
        allowed = sorted(protein_values | {"-"})
        qs = qs.filter(protein_slot_1__in=allowed, protein_slot_2__in=allowed)
    if carb_values:
        allowed = sorted(carb_values | {"-"})
        qs = qs.filter(carb_slot_1__in=allowed, carb_slot_2__in=allowed)
    if fat_values:
        allowed = sorted(fat_values | {"-"})
        qs = qs.filter(fat_slot_1__in=allowed, fat_slot_2__in=allowed)
    return qs


def select_meal_combo_template_for_target(
    *,
    saved_combo: MealComboTemplate,
    meal_target: dict[str, Any] | None,
    is_training_adjacent: bool = False,
    selected_slots: dict[str, Any] | None = None,
    queryset: QuerySet | None = None,
) -> MealComboSelectionDecision:
    """
    Select a preference-compatible combo shape for the meal target.

    Preference compatibility is based on MealComboTemplate slot values. The
    saved combo remains the final fallback so generation does not hard-stop if
    the ideal one-protein or one-carb shape does not exist in the current DB.
    """
    preferred_shape = preferred_combo_shape_for_meal(meal_target, is_training_adjacent=is_training_adjacent)
    compatible_qs = _compatible_combo_queryset(saved_combo=saved_combo, selected_slots=selected_slots, queryset=queryset)
    candidate_count_before = compatible_qs.count()
    filtered_qs = compatible_qs
    fallback_reasons = []

    if preferred_shape.preferred_protein_slot_2 == "-":
        protein_filtered = filtered_qs.filter(protein_slot_2="-")
        if protein_filtered.exists():
            filtered_qs = protein_filtered
        else:
            fallback_reasons.append("no_one_protein_combo_for_preferences")

    if preferred_shape.preferred_carb_slot_2 == "-":
        carb_filtered = filtered_qs.filter(carb_slot_2="-")
        if carb_filtered.exists():
            filtered_qs = carb_filtered
        else:
            fallback_reasons.append("no_one_carb_combo_for_preferences")

    candidate_count_after = filtered_qs.count()
    combo = filtered_qs.order_by("combo_id").first()
    if combo:
        return MealComboSelectionDecision(
            combo=combo,
            preferred_shape=preferred_shape,
            candidate_count_before_filtering=candidate_count_before,
            candidate_count_after_filtering=candidate_count_after,
            fallback_reason=";".join(fallback_reasons) or None,
        )

    fallback_reason = ";".join(fallback_reasons) or "no_preference_compatible_combo"
    fallback_combo = compatible_qs.order_by("combo_id").first() or saved_combo
    return MealComboSelectionDecision(
        combo=fallback_combo,
        preferred_shape=preferred_shape,
        candidate_count_before_filtering=candidate_count_before,
        candidate_count_after_filtering=0,
        fallback_reason=fallback_reason,
    )
