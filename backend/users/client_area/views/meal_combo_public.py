from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.db.models import Q

from core.models import MealComboTemplate
from core.services.meal_combo_lookup import find_meal_combo_id_by_slots
from users.client_area.views.api_contract import error, ok

CHICKEN = "Chicken Breast"
STEAK = "Steak STANDARD"
GROUND_BEEF = "Ground Beef STANDARD"
FISH_CHOICES = ["Salmon", "Tilapia", "Tuna STANDARD"]

PROTEIN_GROUPS = {
    "chicken_only": [CHICKEN],
    "steak_only": [STEAK],
    "ground_beef_only": [GROUND_BEEF],
    "fish_only": FISH_CHOICES,
    "chicken_steak_beef": [CHICKEN, STEAK, GROUND_BEEF],
    "chicken_fish": [CHICKEN, *FISH_CHOICES],
    "chicken_beef_fish_mix": [CHICKEN, STEAK, GROUND_BEEF, *FISH_CHOICES],
}

BASE_CARB_PATTERNS = [
    ("White Rice", "Banana"),
    ("White Rice", "-"),
    ("Brown Rice", "-"),
    ("Brown Rice", "Beans STANDARD"),
]

TEMPLATE_SPECS = [
    {
        "template_key": "starter_chicken_only",
        "name": "Chicken Only",
        "description": "Egg-based meal 1, then chicken meals with rice/pasta carb rotation.",
        "protein_group": "chicken_only",
        "pasta_carb": "Whole Wheat Pasta",
    },
    {
        "template_key": "starter_chicken_steak_beef",
        "name": "Chicken + Steak/Beef",
        "description": "Chicken, steak, and ground beef mix with rice + beans style carb rotation.",
        "protein_group": "chicken_steak_beef",
        "pasta_carb": "Plain Pasta",
    },
    {
        "template_key": "starter_fish_only",
        "name": "Fish Only",
        "description": "Fish-focused meals with the same avocado + oil fat structure.",
        "protein_group": "fish_only",
        "pasta_carb": "Whole Wheat Pasta",
    },
    {
        "template_key": "starter_chicken_fish",
        "name": "Chicken + Fish",
        "description": "Chicken and fish blend with mostly white/brown rice meals.",
        "protein_group": "chicken_fish",
        "pasta_carb": "Plain Pasta",
    },
    {
        "template_key": "starter_chicken_beef_fish_mix",
        "name": "Chicken + Beef/Steak + Fish Mix",
        "description": "Mixed protein library template with rice-heavy meals plus pasta.",
        "protein_group": "chicken_beef_fish_mix",
        "pasta_carb": "Whole Wheat Pasta",
    },
    {
        "template_key": "starter_steak_only",
        "name": "Steak Only",
        "description": "Steak-only pattern with fixed avocado + oil fats.",
        "protein_group": "steak_only",
        "pasta_carb": "Plain Pasta",
    },
    {
        "template_key": "starter_ground_beef_only",
        "name": "Ground Beef Only",
        "description": "Ground beef-only option with your default carb pattern rotation.",
        "protein_group": "ground_beef_only",
        "pasta_carb": "Whole Wheat Pasta",
    },
]


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


def _protein_match_q(values):
    return Q(protein_slot_1__in=values) | Q(protein_slot_2__in=values)


def _pick_combo(
    *,
    carb_1,
    carb_2,
    allowed_proteins,
    preferred_protein=None,
    require_eggs=False,
):
    base = MealComboTemplate.objects.filter(
        carb_slot_1=carb_1,
        carb_slot_2=carb_2,
        fat_slot_1="Avocado",
        fat_slot_2="Oil STANDARD",
    )

    allowed_plus = sorted(set(allowed_proteins or []) | {"-"} | ({"Eggs"} if require_eggs else set()))
    strict = base.filter(protein_slot_1__in=allowed_plus, protein_slot_2__in=allowed_plus)
    if require_eggs:
        strict = strict.filter(_protein_match_q(["Eggs"]))
    if allowed_proteins:
        strict = strict.filter(_protein_match_q(allowed_proteins))
    if preferred_protein:
        strict = strict.filter(_protein_match_q([preferred_protein]))
    combo = strict.order_by("combo_id").first()
    if combo:
        return combo

    relaxed = base
    if require_eggs:
        relaxed = relaxed.filter(_protein_match_q(["Eggs"]))
    if allowed_proteins:
        relaxed = relaxed.filter(_protein_match_q(allowed_proteins))
    if preferred_protein:
        relaxed = relaxed.filter(_protein_match_q([preferred_protein]))
    combo = relaxed.order_by("combo_id").first()
    if combo:
        return combo

    return base.order_by("combo_id").first()


def _build_template(spec):
    protein_cycle = PROTEIN_GROUPS[spec["protein_group"]]
    breakfast_preferred = protein_cycle[0] if protein_cycle else None
    breakfast_combo = _pick_combo(
        carb_1="Quinoa",
        carb_2="Banana",
        allowed_proteins=protein_cycle,
        preferred_protein=breakfast_preferred,
        require_eggs=True,
    )
    if not breakfast_combo:
        return None

    meal_combos = [breakfast_combo]
    carb_patterns = [*BASE_CARB_PATTERNS, (spec["pasta_carb"], "-")]
    for idx, (carb_1, carb_2) in enumerate(carb_patterns):
        preferred_protein = protein_cycle[idx % len(protein_cycle)] if protein_cycle else None
        combo = _pick_combo(
            carb_1=carb_1,
            carb_2=carb_2,
            allowed_proteins=protein_cycle,
            preferred_protein=preferred_protein,
            require_eggs=False,
        )
        if not combo:
            return None
        meal_combos.append(combo)

    return {
        "template_key": spec["template_key"],
        "name": spec["name"],
        "description": (
            f'{spec["description"]} Meal 1 includes Eggs + Quinoa + Banana. '
            "Fats use Avocado + Oil STANDARD."
        ),
        "default_meal_count": 6,
        "default_day_meals": [_combo_to_payload(combo) for combo in meal_combos],
    }


@api_view(["GET"])
@permission_classes([AllowAny])
def meal_combo_starter_templates(request):
    try:
        requested = int(request.query_params.get("count") or len(TEMPLATE_SPECS))
    except (TypeError, ValueError):
        requested = len(TEMPLATE_SPECS)
    count = min(max(requested, 1), len(TEMPLATE_SPECS))

    templates = []
    for spec in TEMPLATE_SPECS:
        built = _build_template(spec)
        if built:
            templates.append(built)
        if len(templates) >= count:
            break

    if not templates:
        return error("NO_COMBOS", "No meal combos available to build starter templates.", http_status=404)
    return ok({"starter_templates": templates})
