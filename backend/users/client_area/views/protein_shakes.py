from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from core.models import FoodLibraryItem, ProteinShakeTemplate
from users.client_area.models import (
    ClientFoodOverride,
    ClientProteinShakeIngredientSelection,
    ClientProteinShakePreference,
)
from users.client_area.views.api_contract import error, ok, require_client


def _decimal_str(value):
    if isinstance(value, Decimal):
        return str(value)
    return str(value or "0")


def _parse_decimal(value, fallback):
    if value in (None, ""):
        return fallback
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("serving_amount must be a valid number.")


def _food_item_payload(row):
    if not row:
        return None
    return {
        "id": row.id,
        "source_food_id": row.source_food_id,
        "name": row.name,
        "display_name": row.display_name or row.name,
        "category": row.category,
        "canonical_category": row.canonical_category,
        "macro": row.macro,
        "measurement_unit": row.measurement_unit,
        "measurement_basis_label": row.measurement_basis_label,
        "protein": _decimal_str(row.protein),
        "carbs": _decimal_str(row.carbs),
        "fats": _decimal_str(row.fats),
    }


def _food_override_payload(row):
    if not row:
        return None
    return {
        "id": row.id,
        "provider": row.external_provider,
        "provider_product_id": row.external_food_id,
        "barcode": row.barcode,
        "display_name": row.display_name,
        "brand_name": row.brand_name,
        "image_url": row.image_url,
        "serving_size": _decimal_str(row.serving_size),
        "serving_unit": row.serving_unit,
        "serving_weight_grams": _decimal_str(row.serving_weight_grams),
        "measurement_basis_label": row.measurement_basis_label,
        "protein": _decimal_str(row.protein),
        "carbs": _decimal_str(row.carbs),
        "fats": _decimal_str(row.fats),
        "calories": _decimal_str(row.calories),
    }


def _slot_payload(slot):
    return {
        "id": slot.id,
        "slot_key": slot.slot_key,
        "display_name": slot.display_name,
        "required": slot.required,
        "default_food_library_item": _food_item_payload(slot.default_food_library_item),
        "default_serving_amount": _decimal_str(slot.default_serving_amount),
        "default_serving_unit": slot.default_serving_unit,
        "allow_user_override": slot.allow_user_override,
        "allow_exclude": slot.allow_exclude,
        "sort_order": slot.sort_order,
        "macro_role": slot.macro_role,
    }


def _template_payload(template):
    return {
        "id": template.id,
        "name": template.name,
        "slug": template.slug,
        "description": template.description,
        "active": template.active,
        "default_scoop_count": template.default_scoop_count,
        "min_scoop_count": template.min_scoop_count,
        "max_scoop_count": template.max_scoop_count,
        "ingredient_slots": [_slot_payload(slot) for slot in template.ingredient_slots.all()],
    }


def _selection_payload(selection):
    return {
        "id": selection.id,
        "slot_id": selection.slot_id,
        "slot_key": selection.slot.slot_key,
        "selected_food_library_item": _food_item_payload(selection.selected_food_library_item),
        "selected_food_override": _food_override_payload(selection.selected_food_override),
        "external_product_data": selection.external_product_data_json,
        "serving_amount": _decimal_str(selection.serving_amount),
        "serving_unit": selection.serving_unit,
        "excluded": selection.excluded,
    }


def _preference_payload(preference):
    return {
        "id": preference.id,
        "template_id": preference.template_id,
        "template_slug": preference.template.slug,
        "enabled": preference.enabled,
        "scoop_count": preference.scoop_count,
        "ingredient_selections": [
            _selection_payload(selection)
            for selection in preference.ingredient_selections.select_related(
                "slot",
                "selected_food_library_item",
                "selected_food_override",
            ).order_by("slot__sort_order", "slot_id")
        ],
    }


def _standard_shake_items_payload():
    names = [
        "Protein Powder STANDARD",
        "Milk STANDARD",
        "Banana STANDARD",
        "Peanut Butter Powder STANDARD",
        "Honey STANDARD",
        "Water STANDARD",
    ]
    rows = FoodLibraryItem.objects.filter(name__in=names, is_active=True).order_by("name")
    return [_food_item_payload(row) for row in rows]


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def client_protein_shake_templates(request):
    auth_error = require_client(request)
    if auth_error:
        return auth_error

    templates = (
        ProteinShakeTemplate.objects.filter(active=True)
        .prefetch_related("ingredient_slots__default_food_library_item")
        .order_by("name")
    )
    preferences = (
        ClientProteinShakePreference.objects.filter(user=request.user)
        .select_related("template")
        .prefetch_related(
            "ingredient_selections__slot",
            "ingredient_selections__selected_food_library_item",
            "ingredient_selections__selected_food_override",
        )
        .order_by("template__name")
    )
    return ok(
        {
            "protein_shake_templates": [_template_payload(template) for template in templates],
            "protein_shake_preferences": [_preference_payload(preference) for preference in preferences],
            "protein_shake_standard_items": _standard_shake_items_payload(),
        }
    )


@api_view(["PUT", "POST"])
@permission_classes([IsAuthenticated])
def client_protein_shake_preference_save(request):
    auth_error = require_client(request)
    if auth_error:
        return auth_error

    payload = request.data or {}
    template_id = payload.get("template_id")
    template_slug = str(payload.get("template_slug") or "").strip()
    template_qs = ProteinShakeTemplate.objects.prefetch_related("ingredient_slots")
    try:
        template = template_qs.get(id=template_id) if template_id else template_qs.get(slug=template_slug)
    except ProteinShakeTemplate.DoesNotExist:
        return error("SHAKE_TEMPLATE_NOT_FOUND", "Protein shake template not found.", http_status=404)

    if not template.active:
        return error("SHAKE_TEMPLATE_INACTIVE", "Protein shake template is not active.", http_status=400)

    scoop_count = None
    raw_scoop_count = payload.get("scoop_count")
    if raw_scoop_count not in (None, ""):
        try:
            scoop_count = int(raw_scoop_count)
        except (TypeError, ValueError):
            return error("INVALID_SCOOP_COUNT", "scoop_count must be 1 or 2.", http_status=400)
        if scoop_count not in (1, 2):
            return error("INVALID_SCOOP_COUNT", "Protein powder scoop count must be 1 or 2.", http_status=400)

    selections_payload = payload.get("ingredient_selections")
    if selections_payload is None:
        selections_payload = payload.get("selections")
    if not isinstance(selections_payload, list):
        selections_payload = []

    slots_by_id = {slot.id: slot for slot in template.ingredient_slots.all()}
    slots_by_key = {slot.slot_key: slot for slot in template.ingredient_slots.all()}

    with transaction.atomic():
        preference, _ = ClientProteinShakePreference.objects.update_or_create(
            user=request.user,
            template=template,
            defaults={
                "enabled": payload.get("enabled") is not False,
                "scoop_count": scoop_count,
            },
        )
        preference.full_clean()
        preference.save()

        for row in selections_payload:
            if not isinstance(row, dict):
                return error("INVALID_SELECTION", "Each ingredient selection must be an object.", http_status=400)
            slot = None
            if row.get("slot_id") is not None:
                try:
                    slot = slots_by_id.get(int(row.get("slot_id")))
                except (TypeError, ValueError):
                    slot = None
            if slot is None:
                slot_key = str(row.get("slot_key") or "").strip()
                slot = slots_by_key.get(slot_key)
            if slot is None:
                return error("INVALID_SLOT", "Ingredient slot must belong to the selected shake template.", http_status=400)

            excluded = row.get("excluded") is True
            if excluded and (slot.required or not slot.allow_exclude):
                return error("REQUIRED_SLOT_CANNOT_BE_EXCLUDED", f"{slot.display_name} cannot be excluded.", http_status=400)

            food_item = None
            food_item_id = row.get("selected_food_library_item_id")
            if food_item_id:
                try:
                    food_item = FoodLibraryItem.objects.get(id=food_item_id, is_active=True)
                except FoodLibraryItem.DoesNotExist:
                    return error("FOOD_LIBRARY_ITEM_NOT_FOUND", "Selected food library item not found.", http_status=404)

            food_override = None
            food_override_id = row.get("selected_food_override_id") or row.get("client_food_override_id")
            if food_override_id:
                try:
                    food_override = ClientFoodOverride.objects.get(id=food_override_id, user=request.user, active=True)
                except ClientFoodOverride.DoesNotExist:
                    return error("FOOD_OVERRIDE_NOT_FOUND", "Selected branded product not found.", http_status=404)

            try:
                serving_amount = _parse_decimal(row.get("serving_amount"), slot.default_serving_amount)
            except ValueError as exc:
                return error("INVALID_SERVING_AMOUNT", str(exc), http_status=400)

            selection, _ = ClientProteinShakeIngredientSelection.objects.update_or_create(
                preference=preference,
                slot=slot,
                defaults={
                    "selected_food_library_item": food_item,
                    "selected_food_override": food_override,
                    "external_product_data_json": row.get("external_product_data") if isinstance(row.get("external_product_data"), dict) else {},
                    "serving_amount": serving_amount,
                    "serving_unit": str(row.get("serving_unit") or slot.default_serving_unit or "").strip(),
                    "excluded": excluded,
                },
            )
            try:
                selection.full_clean()
            except ValidationError as exc:
                return error("INVALID_SELECTION", "Protein shake ingredient selection is invalid.", http_status=400, details=exc.message_dict)
            selection.save()

    preference = (
        ClientProteinShakePreference.objects.select_related("template")
        .prefetch_related(
            "ingredient_selections__slot",
            "ingredient_selections__selected_food_library_item",
            "ingredient_selections__selected_food_override",
        )
        .get(id=preference.id)
    )
    return ok({"protein_shake_preference": _preference_payload(preference)})
