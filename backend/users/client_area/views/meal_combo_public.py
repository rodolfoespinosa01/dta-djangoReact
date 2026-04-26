import logging

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.db.models import Q

from core.models import MealComboTemplate
from core.services.meal_combo_lookup import (
    find_meal_combo_id_by_slots,
    normalize_slots_to_supported_combo_values,
)
from core.services.meal_combo_shape_policy import preferred_combo_shape_for_meal
from users.client_area.views.api_contract import error, ok

logger = logging.getLogger(__name__)

CHICKEN = "Chicken Breast STANDARD"
STEAK = "Steak STANDARD"
GROUND_BEEF = "Ground Beef STANDARD"
EGGS = "Eggs STANDARD"
AVOCADO = "Avocado STANDARD"
OIL = "Oil STANDARD"
FISH_CHOICES = ["Salmon STANDARD", "Tilapia STANDARD", "Tuna STANDARD"]

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
    ("White Rice STANDARD", "Banana STANDARD"),
    ("White Rice STANDARD", "-"),
    ("Brown Rice STANDARD", "-"),
    ("Brown Rice STANDARD", "Beans STANDARD"),
]

ONE_CARB_PATTERNS = [
    ("White Rice STANDARD", "-"),
    ("Brown Rice STANDARD", "-"),
]

TWO_CARB_PATTERNS = [
    ("White Rice STANDARD", "Banana STANDARD"),
    ("Brown Rice STANDARD", "Beans STANDARD"),
]

TEMPLATE_SPECS = [
    {
        "template_key": "starter_chicken_only",
        "name": "Chicken Only",
        "description": "Egg-based meal 1, then chicken meals with rice/pasta carb rotation.",
        "protein_group": "chicken_only",
        "pasta_carb": "Whole Wheat Pasta STANDARD",
    },
    {
        "template_key": "starter_chicken_steak_beef",
        "name": "Chicken + Steak/Beef",
        "description": "Chicken, steak, and ground beef mix with rice + beans style carb rotation.",
        "protein_group": "chicken_steak_beef",
        "pasta_carb": "Plain Pasta STANDARD",
    },
    {
        "template_key": "starter_fish_only",
        "name": "Fish Only",
        "description": "Fish-focused meals with the same avocado + oil fat structure.",
        "protein_group": "fish_only",
        "pasta_carb": "Whole Wheat Pasta STANDARD",
    },
    {
        "template_key": "starter_chicken_fish",
        "name": "Chicken + Fish",
        "description": "Chicken and fish blend with mostly white/brown rice meals.",
        "protein_group": "chicken_fish",
        "pasta_carb": "Plain Pasta STANDARD",
    },
    {
        "template_key": "starter_chicken_beef_fish_mix",
        "name": "Chicken + Beef/Steak + Fish Mix",
        "description": "Mixed protein library template with rice-heavy meals plus pasta.",
        "protein_group": "chicken_beef_fish_mix",
        "pasta_carb": "Whole Wheat Pasta STANDARD",
    },
    {
        "template_key": "starter_steak_only",
        "name": "Steak Only",
        "description": "Steak-only pattern with fixed avocado + oil fats.",
        "protein_group": "steak_only",
        "pasta_carb": "Plain Pasta STANDARD",
    },
    {
        "template_key": "starter_ground_beef_only",
        "name": "Ground Beef Only",
        "description": "Ground beef-only option with your default carb pattern rotation.",
        "protein_group": "ground_beef_only",
        "pasta_carb": "Whole Wheat Pasta STANDARD",
    },
]


def _distinct_values(field_name):
    rows = (
        MealComboTemplate.objects.exclude(**{field_name: ""})
        .values_list(field_name, flat=True)
        .distinct()
        .order_by(field_name)
    )
    seen = set()
    values = []
    for row in rows:
        value = str(row or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        values.append(value)
    # Keep placeholder first if present.
    if "-" in values:
        values = ["-"] + [v for v in values if v != "-"]
    return values


@api_view(["GET"])
@permission_classes([AllowAny])
def meal_combo_slot_options(request):
    slot_categories = {
        "protein_1": _distinct_values("protein_slot_1"),
        "protein_2": _distinct_values("protein_slot_2"),
        "carbs_1": _distinct_values("carb_slot_1"),
        "carbs_2": _distinct_values("carb_slot_2"),
        "fats_1": _distinct_values("fat_slot_1"),
        "fats_2": _distinct_values("fat_slot_2"),
    }

    return ok(
        {
            "slot_options": slot_categories,
            "slot_category_options": slot_categories,
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

    normalized_slots = normalize_slots_to_supported_combo_values(
        {
            "protein_1": payload.get("protein_1"),
            "protein_2": payload.get("protein_2"),
            "carbs_1": payload.get("carbs_1"),
            "carbs_2": payload.get("carbs_2"),
            "fats_1": payload.get("fats_1"),
            "fats_2": payload.get("fats_2"),
        }
    )
    combo_id = find_meal_combo_id_by_slots(**normalized_slots)
    if combo_id is None:
        return ok({"combo_match": {"found": False, "combo_id": None}})
    return ok({"combo_match": {"found": True, "combo_id": combo_id, "slots": normalized_slots}})


def _combo_to_payload(combo):
    return {
        "combo_id": combo.combo_id,
        "protein_1": (combo.protein_slot_1 or "-").strip() or "-",
        "protein_2": (combo.protein_slot_2 or "-").strip() or "-",
        "carbs_1": (combo.carb_slot_1 or "-").strip() or "-",
        "carbs_2": (combo.carb_slot_2 or "-").strip() or "-",
        "fats_1": (combo.fat_slot_1 or "-").strip() or "-",
        "fats_2": (combo.fat_slot_2 or "-").strip() or "-",
        "combo_match": "matched",
    }


def _meal_targets_from_day_payload(day_payload):
    targets = {}
    if not isinstance(day_payload, dict):
        return targets
    for row in day_payload.get("meal_macro_splits") or []:
        if not isinstance(row, dict):
            continue
        try:
            meal_number = int(row.get("meal_number") or 0)
        except (TypeError, ValueError):
            continue
        if meal_number < 1:
            continue
        grams = row.get("grams") if isinstance(row.get("grams"), dict) else {}
        targets[meal_number] = {
            "protein": grams.get("protein_g") or 0,
            "carbs": grams.get("carbs_g") or 0,
            "fats": grams.get("fats_g") or 0,
        }
    return targets


def _training_adjacent_meals(day_payload):
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


def _target_for_meal(day_payload, meal_number):
    return _meal_targets_from_day_payload(day_payload).get(meal_number)


def _filter_for_shape(qs, shape):
    filtered = qs
    fallback_reasons = []

    if shape.preferred_protein_slot_2 == "-":
        protein_filtered = filtered.filter(protein_slot_2="-")
        if protein_filtered.exists():
            filtered = protein_filtered
        else:
            fallback_reasons.append("no_one_protein_starter_combo")

    if shape.preferred_carb_slot_2 == "-":
        carb_filtered = filtered.filter(carb_slot_2="-")
        if carb_filtered.exists():
            filtered = carb_filtered
        else:
            fallback_reasons.append("no_one_carb_starter_combo")

    return filtered, fallback_reasons


def _protein_match_q(values):
    return Q(protein_slot_1__in=values) | Q(protein_slot_2__in=values)


def _pick_combo(
    *,
    carb_1,
    carb_2,
    allowed_proteins,
    preferred_protein=None,
    require_eggs=False,
    meal_target=None,
    is_training_adjacent=False,
    debug_context=None,
):
    base = MealComboTemplate.objects.filter(
        carb_slot_1=carb_1,
        carb_slot_2=carb_2,
        fat_slot_1=AVOCADO,
        fat_slot_2=OIL,
    )

    allowed_plus = sorted(set(allowed_proteins or []) | {"-"} | ({EGGS} if require_eggs else set()))
    strict = base.filter(protein_slot_1__in=allowed_plus, protein_slot_2__in=allowed_plus)
    if require_eggs:
        strict = strict.filter(_protein_match_q([EGGS]))
    if allowed_proteins:
        strict = strict.filter(_protein_match_q(allowed_proteins))
    if preferred_protein:
        strict = strict.filter(_protein_match_q([preferred_protein]))
    shape = preferred_combo_shape_for_meal(meal_target, is_training_adjacent=is_training_adjacent)
    candidates_before = strict.count()
    shaped, fallback_reasons = _filter_for_shape(strict, shape)
    candidates_after = shaped.count()
    combo = shaped.order_by("combo_id").first()
    if combo:
        _log_starter_selection(
            debug_context=debug_context,
            meal_target=meal_target,
            is_training_adjacent=is_training_adjacent,
            shape=shape,
            candidates_before=candidates_before,
            candidates_after=candidates_after,
            combo=combo,
            fallback_reason=";".join(fallback_reasons) or None,
        )
        return combo

    relaxed = base
    if require_eggs:
        relaxed = relaxed.filter(_protein_match_q([EGGS]))
    if allowed_proteins:
        relaxed = relaxed.filter(_protein_match_q(allowed_proteins))
    if preferred_protein:
        relaxed = relaxed.filter(_protein_match_q([preferred_protein]))
    relaxed_before = relaxed.count()
    relaxed_shaped, relaxed_fallback_reasons = _filter_for_shape(relaxed, shape)
    combo = relaxed_shaped.order_by("combo_id").first()
    if combo:
        _log_starter_selection(
            debug_context=debug_context,
            meal_target=meal_target,
            is_training_adjacent=is_training_adjacent,
            shape=shape,
            candidates_before=relaxed_before,
            candidates_after=relaxed_shaped.count(),
            combo=combo,
            fallback_reason=";".join([*fallback_reasons, *relaxed_fallback_reasons, "relaxed_protein_match"]) or "relaxed_protein_match",
        )
        return combo

    base_before = base.count()
    base_shaped, base_fallback_reasons = _filter_for_shape(base, shape)
    combo = base_shaped.order_by("combo_id").first() or base.order_by("combo_id").first()
    if combo:
        _log_starter_selection(
            debug_context=debug_context,
            meal_target=meal_target,
            is_training_adjacent=is_training_adjacent,
            shape=shape,
            candidates_before=base_before,
            candidates_after=base_shaped.count(),
            combo=combo,
            fallback_reason=";".join([*fallback_reasons, *base_fallback_reasons, "base_combo_fallback"]),
        )
    return combo


def _log_starter_selection(
    *,
    debug_context,
    meal_target,
    is_training_adjacent,
    shape,
    candidates_before,
    candidates_after,
    combo,
    fallback_reason=None,
):
    if not combo:
        return
    context = debug_context or {}
    logger.info(
        "Starter meal combo selection: day=%s meal=%s protein_target=%s carb_target=%s "
        "training_context=%s preferred_protein=%s preferred_carb=%s candidates_before=%s "
        "candidates_after=%s chosen_combo_id=%s protein_slots=%s/%s carb_slots=%s/%s fallback_reason=%s",
        context.get("day"),
        context.get("meal_number"),
        (meal_target or {}).get("protein"),
        (meal_target or {}).get("carbs"),
        context.get("training_context"),
        shape.protein_structure,
        shape.carb_structure,
        candidates_before,
        candidates_after,
        combo.combo_id,
        combo.protein_slot_1,
        combo.protein_slot_2,
        combo.carb_slot_1,
        combo.carb_slot_2,
        fallback_reason,
    )


def _carb_patterns_for_shape(shape, pasta_carb):
    if shape.preferred_carb_slot_2 == "-":
        return [*ONE_CARB_PATTERNS, (pasta_carb, "-")]
    return [*TWO_CARB_PATTERNS, *ONE_CARB_PATTERNS, (pasta_carb, "-")]


def _build_template(spec, day_payload=None):
    protein_cycle = PROTEIN_GROUPS[spec["protein_group"]]
    breakfast_preferred = protein_cycle[0] if protein_cycle else None
    training_adjacent = _training_adjacent_meals(day_payload)
    day = (day_payload or {}).get("day") if isinstance(day_payload, dict) else None
    meal_1_target = _target_for_meal(day_payload, 1)
    breakfast_combo = _pick_combo(
        carb_1="Quinoa STANDARD" if preferred_combo_shape_for_meal(meal_1_target, 1 in training_adjacent).preferred_carb_slot_2 != "-" else "White Rice STANDARD",
        carb_2="Banana STANDARD" if preferred_combo_shape_for_meal(meal_1_target, 1 in training_adjacent).preferred_carb_slot_2 != "-" else "-",
        allowed_proteins=protein_cycle,
        preferred_protein=breakfast_preferred,
        require_eggs=preferred_combo_shape_for_meal(meal_1_target, 1 in training_adjacent).preferred_protein_slot_2 != "-",
        meal_target=meal_1_target,
        is_training_adjacent=1 in training_adjacent,
        debug_context={"day": day, "meal_number": 1, "training_context": (day_payload or {}).get("training_before_meal") or "no_training"},
    )
    if not breakfast_combo:
        return None

    meal_combos = [breakfast_combo]
    default_meal_count = int((day_payload or {}).get("meals_per_day") or 6) if isinstance(day_payload, dict) else 6
    default_meal_count = default_meal_count if default_meal_count in (3, 4, 5, 6) else 6
    for meal_number in range(2, default_meal_count + 1):
        meal_target = _target_for_meal(day_payload, meal_number)
        shape = preferred_combo_shape_for_meal(meal_target, meal_number in training_adjacent)
        carb_patterns = _carb_patterns_for_shape(shape, spec["pasta_carb"])
        carb_1, carb_2 = carb_patterns[(meal_number - 2) % len(carb_patterns)]
        idx = meal_number - 2
        preferred_protein = protein_cycle[idx % len(protein_cycle)] if protein_cycle else None
        combo = _pick_combo(
            carb_1=carb_1,
            carb_2=carb_2,
            allowed_proteins=protein_cycle,
            preferred_protein=preferred_protein,
            require_eggs=False,
            meal_target=meal_target,
            is_training_adjacent=meal_number in training_adjacent,
            debug_context={
                "day": day,
                "meal_number": meal_number,
                "training_context": (day_payload or {}).get("training_before_meal") or "no_training",
            },
        )
        if not combo:
            return None
        meal_combos.append(combo)

    return {
        "template_key": spec["template_key"],
        "name": spec["name"],
        "description": (
            f'{spec["description"]} Meal slots adapt to the selected day macro targets. '
            "Fats use Avocado + Oil STANDARD when available."
        ),
        "default_meal_count": default_meal_count,
        "default_day_meals": [_combo_to_payload(combo) for combo in meal_combos],
    }


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def meal_combo_starter_templates(request):
    try:
        requested = int(request.query_params.get("count") or len(TEMPLATE_SPECS))
    except (TypeError, ValueError):
        requested = len(TEMPLATE_SPECS)
    count = min(max(requested, 1), len(TEMPLATE_SPECS))

    day_payload = (request.data or {}).get("day_payload") if request.method == "POST" else None
    if day_payload is not None and not isinstance(day_payload, dict):
        return error("INVALID_DAY_PAYLOAD", "day_payload must be an object.", http_status=400)

    templates = []
    for spec in TEMPLATE_SPECS:
        built = _build_template(spec, day_payload=day_payload)
        if built:
            templates.append(built)
        if len(templates) >= count:
            break

    if not templates:
        return error("NO_COMBOS", "No meal combos available to build starter templates.", http_status=404)
    return ok({"starter_templates": templates})
