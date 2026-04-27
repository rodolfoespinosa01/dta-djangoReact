from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from core.models import FoodLibraryItem, MealComboTemplate
from core.services.food_canonical import canonical_standard_name

MEAL_COMBO_SLOT_KEYS = ("protein_1", "protein_2", "carbs_1", "carbs_2", "fats_1", "fats_2")
TEMPLATE_FIELD_BY_SLOT = {
    "protein_1": "protein_slot_1",
    "protein_2": "protein_slot_2",
    "carbs_1": "carb_slot_1",
    "carbs_2": "carb_slot_2",
    "fats_1": "fat_slot_1",
    "fats_2": "fat_slot_2",
}


def _normalize_slot(value: Any) -> str:
    normalized = str(value or "").strip()
    return normalized or "-"


def _ordered_distinct(values: Iterable[Any]) -> list[str]:
    seen = set()
    ordered = []
    for value in values:
        normalized = _normalize_slot(value)
        if normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    if "-" in seen:
        ordered = ["-"] + [value for value in ordered if value != "-"]
    return ordered


def get_supported_combo_slot_values() -> dict[str, list[str]]:
    supported = {}
    for slot_key, field_name in TEMPLATE_FIELD_BY_SLOT.items():
        supported[slot_key] = _ordered_distinct(
            MealComboTemplate.objects.exclude(**{field_name: ""})
            .values_list(field_name, flat=True)
            .distinct()
            .order_by(field_name)
        )
    return supported


def _supported_set(supported_values: dict[str, Iterable[str]], slot_key: str) -> set[str]:
    return {_normalize_slot(value) for value in supported_values.get(slot_key, [])}


def _food_alias_to_combo_category() -> dict[str, str]:
    rows = FoodLibraryItem.objects.filter(
        is_active=True,
        is_standard=True,
        approval_status=FoodLibraryItem.ApprovalStatus.APPROVED,
    )
    alias_map: dict[str, str] = {}
    for row in rows:
        category = _normalize_slot(row.canonical_category or row.category)
        if category == "-":
            continue
        for raw_alias in (row.display_name, row.name, row.canonical_name, row.canonical_category, row.category):
            alias = _normalize_slot(raw_alias)
            if alias != "-" and alias not in alias_map:
                alias_map[alias] = category
    return alias_map


def normalize_slots_to_supported_combo_values(
    slots: dict[str, Any],
    *,
    supported_values: dict[str, Iterable[str]] | None = None,
) -> dict[str, str]:
    supported_values = supported_values or get_supported_combo_slot_values()
    food_aliases = _food_alias_to_combo_category()
    normalized_slots = {}

    for slot_key in MEAL_COMBO_SLOT_KEYS:
        value = _normalize_slot((slots or {}).get(slot_key))
        supported = _supported_set(supported_values, slot_key)
        if value in supported:
            normalized_slots[slot_key] = value
            continue

        alias_value = food_aliases.get(value)
        if alias_value and alias_value in supported:
            normalized_slots[slot_key] = alias_value
            continue

        canonical_value = canonical_standard_name(value)
        normalized_slots[slot_key] = canonical_value if canonical_value in supported else value

    return normalized_slots


def find_meal_combo_template_by_slots(*, protein_1, protein_2, carbs_1, carbs_2, fats_1, fats_2):
    return MealComboTemplate.objects.filter(
        protein_slot_1=_normalize_slot(protein_1),
        protein_slot_2=_normalize_slot(protein_2),
        carb_slot_1=_normalize_slot(carbs_1),
        carb_slot_2=_normalize_slot(carbs_2),
        fat_slot_1=_normalize_slot(fats_1),
        fat_slot_2=_normalize_slot(fats_2),
    ).first()


def find_meal_combo_id_by_slots(**kwargs):
    combo = find_meal_combo_template_by_slots(**kwargs)
    return combo.combo_id if combo else None
