from core.models import MealComboTemplate


def _normalize_slot(value):
    normalized = str(value or "").strip()
    return normalized or "-"


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
