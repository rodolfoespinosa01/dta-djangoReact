import copy
from decimal import Decimal

from django.db import transaction

from core.models import CarbCyclingDefault, KetoDefault, StandardDefault, TDEEDefault
from core.seed_data.admin_parameter_defaults import get_admin_parameter_defaults_v1
from users.admin_area.models import (
    AdminCarbCyclingSettings,
    AdminKetoSettings,
    AdminStandardSettings,
    AdminTDEESettings,
)


GOAL_ORDER = ("lose", "maintain", "gain")


def _json_ready(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    return value


def _goal_sort_key(goal):
    try:
        return GOAL_ORDER.index(goal)
    except ValueError:
        return len(GOAL_ORDER)


def _load_admin_rows(admin):
    tdee_record = AdminTDEESettings.objects.filter(admin=admin).first()
    standard_records = list(AdminStandardSettings.objects.filter(admin=admin))
    keto_records = list(AdminKetoSettings.objects.filter(admin=admin))
    carb_records = list(AdminCarbCyclingSettings.objects.filter(admin=admin))
    return tdee_record, standard_records, keto_records, carb_records


def _state_from_rows(tdee_record, standard_records, keto_records, carb_records):
    rows = [row for row in [tdee_record, *standard_records, *keto_records, *carb_records] if row is not None]
    if not rows:
        return {
            "exists": False,
            "initialized": False,
            "defaults_version_applied": None,
            "created_at": None,
            "updated_at": None,
        }
    return {
        "exists": True,
        "initialized": bool(getattr(tdee_record, "initialized", False)),
        "defaults_version_applied": getattr(tdee_record, "defaults_version_applied", None) or "v1",
        "created_at": min(row.created_at for row in rows),
        "updated_at": max(row.updated_at for row in rows),
    }


def split_admin_parameter_payload(payload):
    source = copy.deepcopy(payload or {})
    version = source.get("version", "v1")
    meal_plans = source.get("meal_plans") or {}
    standard_payload = meal_plans.get("standard") or {}
    keto_payload = meal_plans.get("keto") or {}
    carb_payload = meal_plans.get("carb_cycling") or {}

    tdee_data = {
        "version": version,
        "lose_weight_percent": (source.get("goal_calorie_adjustments") or {}).get("lose_weight_percent", -15),
        "maintain_weight_percent": (source.get("goal_calorie_adjustments") or {}).get("maintain_weight_percent", 0),
        "gain_weight_percent": (source.get("goal_calorie_adjustments") or {}).get("gain_weight_percent", 20),
        "category_multipliers_json": copy.deepcopy((source.get("tdee") or {}).get("category_multipliers") or {}),
        "category_mapping_by_lifestyle_and_training_days_json": copy.deepcopy(
            (source.get("tdee") or {}).get("category_mapping_by_lifestyle_and_training_days") or {}
        ),
        "weekly_day_multiplier_splits_json": copy.deepcopy(
            (source.get("tdee") or {}).get("weekly_day_multiplier_splits") or {}
        ),
    }

    standard_rows = []
    standard_distribution = copy.deepcopy(standard_payload.get("meal_macro_distribution") or {})
    for goal, rule in (standard_payload.get("macro_rules_by_goal") or {}).items():
        standard_rows.append(
            {
                "version": version,
                "goal": goal,
                "protein_factor_unit": rule.get("protein_factor_unit", "g_per_lb"),
                "protein_factor_value": rule.get("protein_factor_value", 1),
                "carb_percent": rule.get("carb_percent", 0),
                "fat_percent": rule.get("fat_percent", 0),
                "meal_macro_distribution_json": copy.deepcopy(standard_distribution),
            }
        )

    keto_rows = []
    keto_distribution = copy.deepcopy(keto_payload.get("meal_macro_distribution") or {})
    for goal, rule in (keto_payload.get("macro_rules_by_goal") or {}).items():
        keto_rows.append(
            {
                "version": version,
                "goal": goal,
                "protein_factor_unit": rule.get("protein_factor_unit", "g_per_lb"),
                "protein_factor_value": rule.get("protein_factor_value", 1),
                "carb_percent": rule.get("carb_percent", 0),
                "fat_percent": rule.get("fat_percent", 0),
                "meal_macro_distribution_json": copy.deepcopy(keto_distribution),
            }
        )

    carb_rows = []
    carb_distribution = copy.deepcopy(carb_payload.get("meal_macro_distribution") or {})
    for goal, rule in (carb_payload.get("macro_rules_by_goal") or {}).items():
        low_day = rule.get("low_day") or {}
        high_day = rule.get("high_day") or {}
        carb_rows.append(
            {
                "version": version,
                "goal": goal,
                "protein_factor_unit": rule.get("protein_factor_unit", "g_per_lb"),
                "protein_factor_value": rule.get("protein_factor_value", 1),
                "low_day_carb_percent": low_day.get("carb_percent", 0),
                "low_day_fat_percent": low_day.get("fat_percent", 0),
                "high_day_carb_percent": high_day.get("carb_percent", 0),
                "high_day_fat_percent": high_day.get("fat_percent", 0),
                "meal_macro_distribution_json": copy.deepcopy(carb_distribution),
            }
        )

    return {
        "version": version,
        "tdee": tdee_data,
        "standard": sorted(standard_rows, key=lambda row: _goal_sort_key(row["goal"])),
        "keto": sorted(keto_rows, key=lambda row: _goal_sort_key(row["goal"])),
        "carb_cycling": sorted(carb_rows, key=lambda row: _goal_sort_key(row["goal"])),
    }


def _build_payload_from_records(*, version, tdee_record, standard_records, keto_records, carb_records):
    standard_records = sorted(standard_records, key=lambda row: _goal_sort_key(row.goal))
    keto_records = sorted(keto_records, key=lambda row: _goal_sort_key(row.goal))
    carb_records = sorted(carb_records, key=lambda row: _goal_sort_key(row.goal))

    return _json_ready({
        "version": version,
        "goal_calorie_adjustments": {
            "lose_weight_percent": tdee_record.lose_weight_percent,
            "maintain_weight_percent": tdee_record.maintain_weight_percent,
            "gain_weight_percent": tdee_record.gain_weight_percent,
        },
        "tdee": {
            "category_multipliers": copy.deepcopy(tdee_record.category_multipliers_json or {}),
            "category_mapping_by_lifestyle_and_training_days": copy.deepcopy(
                tdee_record.category_mapping_by_lifestyle_and_training_days_json or {}
            ),
            "weekly_day_multiplier_splits": copy.deepcopy(tdee_record.weekly_day_multiplier_splits_json or {}),
        },
        "meal_plans": {
            "standard": {
                "macro_rules_by_goal": {
                    row.goal: {
                        "protein_factor_unit": row.protein_factor_unit,
                        "protein_factor_value": row.protein_factor_value,
                        "carb_percent": row.carb_percent,
                        "fat_percent": row.fat_percent,
                    }
                    for row in standard_records
                },
                "meal_macro_distribution": copy.deepcopy(
                    standard_records[0].meal_macro_distribution_json if standard_records else {}
                ),
            },
            "keto": {
                "macro_rules_by_goal": {
                    row.goal: {
                        "protein_factor_unit": row.protein_factor_unit,
                        "protein_factor_value": row.protein_factor_value,
                        "carb_percent": row.carb_percent,
                        "fat_percent": row.fat_percent,
                    }
                    for row in keto_records
                },
                "meal_macro_distribution": copy.deepcopy(
                    keto_records[0].meal_macro_distribution_json if keto_records else {}
                ),
            },
            "carb_cycling": {
                "macro_rules_by_goal": {
                    row.goal: {
                        "protein_factor_unit": row.protein_factor_unit,
                        "protein_factor_value": row.protein_factor_value,
                        "low_day": {
                            "carb_percent": row.low_day_carb_percent,
                            "fat_percent": row.low_day_fat_percent,
                        },
                        "high_day": {
                            "carb_percent": row.high_day_carb_percent,
                            "fat_percent": row.high_day_fat_percent,
                        },
                    }
                    for row in carb_records
                },
                "meal_macro_distribution": copy.deepcopy(
                    carb_records[0].meal_macro_distribution_json if carb_records else {}
                ),
            },
        },
    })


def _core_defaults_complete(version="v1"):
    return (
        TDEEDefault.objects.filter(version=version).exists()
        and StandardDefault.objects.filter(version=version).count() >= len(GOAL_ORDER)
        and KetoDefault.objects.filter(version=version).count() >= len(GOAL_ORDER)
        and CarbCyclingDefault.objects.filter(version=version).count() >= len(GOAL_ORDER)
    )


def _admin_tables_complete(admin, *, tdee_record=None, standard_records=None, keto_records=None, carb_records=None):
    if tdee_record is None or standard_records is None or keto_records is None or carb_records is None:
        tdee_record, standard_records, keto_records, carb_records = _load_admin_rows(admin)
    return (
        tdee_record is not None
        and len(standard_records) >= len(GOAL_ORDER)
        and len(keto_records) >= len(GOAL_ORDER)
        and len(carb_records) >= len(GOAL_ORDER)
    )


def get_core_admin_parameter_payload(version="v1"):
    if not _core_defaults_complete(version=version):
        return get_admin_parameter_defaults_v1()

    tdee_record = TDEEDefault.objects.get(version=version)
    standard_records = list(StandardDefault.objects.filter(version=version))
    keto_records = list(KetoDefault.objects.filter(version=version))
    carb_records = list(CarbCyclingDefault.objects.filter(version=version))
    return _build_payload_from_records(
        version=version,
        tdee_record=tdee_record,
        standard_records=standard_records,
        keto_records=keto_records,
        carb_records=carb_records,
    )


@transaction.atomic
def seed_core_admin_parameter_defaults(version="v1"):
    payload = get_admin_parameter_defaults_v1()
    sections = split_admin_parameter_payload(payload)

    TDEEDefault.objects.update_or_create(
        version=version,
        defaults={k: v for k, v in sections["tdee"].items() if k != "version"},
    )

    StandardDefault.objects.filter(version=version).exclude(
        goal__in=[row["goal"] for row in sections["standard"]]
    ).delete()
    for row in sections["standard"]:
        defaults = {k: v for k, v in row.items() if k not in {"version", "goal"}}
        StandardDefault.objects.update_or_create(
            version=version,
            goal=row["goal"],
            defaults=defaults,
        )

    KetoDefault.objects.filter(version=version).exclude(
        goal__in=[row["goal"] for row in sections["keto"]]
    ).delete()
    for row in sections["keto"]:
        defaults = {k: v for k, v in row.items() if k not in {"version", "goal"}}
        KetoDefault.objects.update_or_create(
            version=version,
            goal=row["goal"],
            defaults=defaults,
        )

    CarbCyclingDefault.objects.filter(version=version).exclude(
        goal__in=[row["goal"] for row in sections["carb_cycling"]]
    ).delete()
    for row in sections["carb_cycling"]:
        defaults = {k: v for k, v in row.items() if k not in {"version", "goal"}}
        CarbCyclingDefault.objects.update_or_create(
            version=version,
            goal=row["goal"],
            defaults=defaults,
        )

    return get_core_admin_parameter_payload(version=version)


@transaction.atomic
def apply_admin_parameter_payload(admin, payload, *, initialized=True):
    source = _json_ready(copy.deepcopy(payload or {}))
    version = source.get("version", "v1")
    sections = split_admin_parameter_payload(source)

    AdminTDEESettings.objects.update_or_create(
        admin=admin,
        defaults={
            "initialized": initialized,
            "defaults_version_applied": version,
            "lose_weight_percent": sections["tdee"]["lose_weight_percent"],
            "maintain_weight_percent": sections["tdee"]["maintain_weight_percent"],
            "gain_weight_percent": sections["tdee"]["gain_weight_percent"],
            "category_multipliers_json": sections["tdee"]["category_multipliers_json"],
            "category_mapping_by_lifestyle_and_training_days_json": sections["tdee"]["category_mapping_by_lifestyle_and_training_days_json"],
            "weekly_day_multiplier_splits_json": sections["tdee"]["weekly_day_multiplier_splits_json"],
        },
    )

    AdminStandardSettings.objects.filter(admin=admin).exclude(
        goal__in=[row["goal"] for row in sections["standard"]]
    ).delete()
    for row in sections["standard"]:
        AdminStandardSettings.objects.update_or_create(
            admin=admin,
            goal=row["goal"],
            defaults={
                "defaults_version_applied": version,
                "protein_factor_unit": row["protein_factor_unit"],
                "protein_factor_value": row["protein_factor_value"],
                "carb_percent": row["carb_percent"],
                "fat_percent": row["fat_percent"],
                "meal_macro_distribution_json": row["meal_macro_distribution_json"],
            },
        )

    AdminKetoSettings.objects.filter(admin=admin).exclude(
        goal__in=[row["goal"] for row in sections["keto"]]
    ).delete()
    for row in sections["keto"]:
        AdminKetoSettings.objects.update_or_create(
            admin=admin,
            goal=row["goal"],
            defaults={
                "defaults_version_applied": version,
                "protein_factor_unit": row["protein_factor_unit"],
                "protein_factor_value": row["protein_factor_value"],
                "carb_percent": row["carb_percent"],
                "fat_percent": row["fat_percent"],
                "meal_macro_distribution_json": row["meal_macro_distribution_json"],
            },
        )

    AdminCarbCyclingSettings.objects.filter(admin=admin).exclude(
        goal__in=[row["goal"] for row in sections["carb_cycling"]]
    ).delete()
    for row in sections["carb_cycling"]:
        AdminCarbCyclingSettings.objects.update_or_create(
            admin=admin,
            goal=row["goal"],
            defaults={
                "defaults_version_applied": version,
                "protein_factor_unit": row["protein_factor_unit"],
                "protein_factor_value": row["protein_factor_value"],
                "low_day_carb_percent": row["low_day_carb_percent"],
                "low_day_fat_percent": row["low_day_fat_percent"],
                "high_day_carb_percent": row["high_day_carb_percent"],
                "high_day_fat_percent": row["high_day_fat_percent"],
                "meal_macro_distribution_json": row["meal_macro_distribution_json"],
            },
        )

    return admin_parameter_state(admin)


def ensure_admin_parameter_tables(admin):
    tdee_record, standard_records, keto_records, carb_records = _load_admin_rows(admin)
    if _admin_tables_complete(
        admin,
        tdee_record=tdee_record,
        standard_records=standard_records,
        keto_records=keto_records,
        carb_records=carb_records,
    ):
        return _state_from_rows(tdee_record, standard_records, keto_records, carb_records)

    version = getattr(tdee_record, "defaults_version_applied", None) or "v1"
    return reset_admin_parameter_payload_to_defaults(admin, version=version)


def get_admin_parameter_payload(admin, *, ensure_exists=True):
    if ensure_exists:
        ensure_admin_parameter_tables(admin)
    tdee_record, standard_records, keto_records, carb_records = _load_admin_rows(admin)
    if not _admin_tables_complete(
        admin,
        tdee_record=tdee_record,
        standard_records=standard_records,
        keto_records=keto_records,
        carb_records=carb_records,
    ):
        return get_core_admin_parameter_payload()

    version = getattr(tdee_record, "defaults_version_applied", "v1") or "v1"
    return _build_payload_from_records(
        version=version,
        tdee_record=tdee_record,
        standard_records=standard_records,
        keto_records=keto_records,
        carb_records=carb_records,
    )


def reset_admin_parameter_payload_to_defaults(admin, *, version="v1"):
    payload = get_core_admin_parameter_payload(version=version)
    return apply_admin_parameter_payload(admin, payload, initialized=True)


def admin_parameter_state(admin):
    tdee_record, standard_records, keto_records, carb_records = _load_admin_rows(admin)
    return _state_from_rows(tdee_record, standard_records, keto_records, carb_records)