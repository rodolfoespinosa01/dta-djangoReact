import random

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.db.models import Q

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


def _combo_to_payload(combo):
    return {
        "combo_id": combo.combo_id,
        "protein_1": combo.protein_slot_1 or "-",
        "protein_2": combo.protein_slot_2 or "-",
        "carbs_1": combo.carb_slot_1 or "-",
        "carbs_2": combo.carb_slot_2 or "-",
        "fats_1": combo.fat_slot_1 or "-",
        "fats_2": combo.fat_slot_2 or "-",
        "combo_match": "matched",
    }


def _pick_random(rows, count, rng):
    rows = list(rows)
    if not rows:
        return []
    if len(rows) <= count:
        return rows
    return rng.sample(rows, count)


def _meal_combo_queryset_breakfast():
    return MealComboTemplate.objects.filter(
        Q(protein_slot_1__in=["Eggs", "Egg Whites"])
        | Q(protein_slot_2__in=["Eggs", "Egg Whites"])
        | Q(carb_slot_1__in=["Banana"])
        | Q(carb_slot_2__in=["Banana"])
    )


def _meal_combo_queryset_lunch_dinner():
    return MealComboTemplate.objects.exclude(
        Q(protein_slot_1__in=["Eggs", "Egg Whites"]) & Q(carb_slot_1="Banana")
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def meal_combo_starter_templates(request):
    """
    Generate global starter templates from the current combo library.
    Meal 1 uses breakfast-style combos; meals 2-6 use lunch/dinner combos.
    """
    count = min(max(int(request.query_params.get("count", 5) or 5), 1), 10)
    seed = (request.query_params.get("seed") or "dta").strip()
    rng = random.Random(seed)

    breakfasts = list(_meal_combo_queryset_breakfast().order_by("combo_id")[:1200])
    lunches = list(_meal_combo_queryset_lunch_dinner().order_by("combo_id")[:3000])
    if not breakfasts:
        breakfasts = list(MealComboTemplate.objects.order_by("combo_id")[:500])
    if not lunches:
        lunches = list(MealComboTemplate.objects.order_by("combo_id")[:500])

    breakfasts = _pick_random(breakfasts, max(count * 2, 8), rng)
    lunches = _pick_random(lunches, max(count * 8, 40), rng)
    if not breakfasts or not lunches:
        return error("NO_COMBOS", "No meal combos available to build starter templates.", http_status=404)

    breakfast_labels = ["Egg Start", "Balanced Breakfast", "Quick Breakfast", "Protein Morning", "Banana Breakfast"]
    lunch_labels = ["Balanced Prep", "Lean Lunch", "Steady Fuel", "Classic Meal", "Dinner Prep", "High Protein"]

    templates = []
    for idx in range(count):
        breakfast_combo = breakfasts[idx % len(breakfasts)]
        meal_rows = [_combo_to_payload(breakfast_combo)]
        # pick five lunch/dinner combos with a rolling offset for variety
        start = (idx * 5) % len(lunches)
        for j in range(5):
            combo = lunches[(start + j) % len(lunches)]
            meal_rows.append(_combo_to_payload(combo))

        templates.append(
            {
                "template_key": f"starter_{idx + 1}",
                "name": f"{breakfast_labels[idx % len(breakfast_labels)]} + {lunch_labels[idx % len(lunch_labels)]}",
                "description": "Meal 1 starts breakfast-style; meals 2-6 use lunch/dinner combos. Edit any meal after applying.",
                "default_meal_count": 6,
                "default_day_meals": meal_rows,
            }
        )

    return ok({"starter_templates": templates})
