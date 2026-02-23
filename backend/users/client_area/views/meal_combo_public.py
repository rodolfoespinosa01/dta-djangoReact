from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from core.models import MealComboTemplate
from core.services.meal_combo_lookup import find_meal_combo_id_by_slots
from users.client_area.views.api_contract import error, ok


def _distinct_values(field_name):
    values = (
        MealComboTemplate.objects.exclude(**{field_name: ""})
        .values_list(field_name, flat=True)
        .distinct()
        .order_by(field_name)
    )
    values = [str(v).strip() for v in values if str(v).strip()]
    # Keep placeholder first if present.
    if "-" in values:
        values = ["-"] + [v for v in values if v != "-"]
    return values


@api_view(["GET"])
@permission_classes([AllowAny])
def meal_combo_slot_options(request):
    return ok(
        {
            "slot_options": {
                "protein_1": _distinct_values("protein_slot_1"),
                "protein_2": _distinct_values("protein_slot_2"),
                "carbs_1": _distinct_values("carb_slot_1"),
                "carbs_2": _distinct_values("carb_slot_2"),
                "fats_1": _distinct_values("fat_slot_1"),
                "fats_2": _distinct_values("fat_slot_2"),
            }
        }
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def meal_combo_lookup(request):
    payload = request.data or {}
    required = ["protein_1", "protein_2", "carbs_1", "carbs_2", "fats_1", "fats_2"]
    missing = [key for key in required if key not in payload]
    if missing:
        return error("MISSING_FIELDS", "Missing combo slot fields.", http_status=400, details={"missing": missing})

    combo_id = find_meal_combo_id_by_slots(
        protein_1=payload.get("protein_1"),
        protein_2=payload.get("protein_2"),
        carbs_1=payload.get("carbs_1"),
        carbs_2=payload.get("carbs_2"),
        fats_1=payload.get("fats_1"),
        fats_2=payload.get("fats_2"),
    )
    if combo_id is None:
        return ok({"combo_match": {"found": False, "combo_id": None}})
    return ok({"combo_match": {"found": True, "combo_id": combo_id}})

