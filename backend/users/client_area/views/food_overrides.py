from decimal import Decimal

from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from core.services.food_canonical import canonical_standard_name
from core.services.meal_combo_lookup import get_supported_combo_slot_values
from core.services.usda_fooddata import USDAFoodDataError, get_food_details, search_foods
from users.client_area.models import ClientFoodOverride
from users.client_area.views.api_contract import error, ok, require_client


def _decimal_str(value):
    if isinstance(value, Decimal):
        return str(value)
    return str(value or "0")


def _override_payload(row: ClientFoodOverride) -> dict:
    return {
        "id": row.id,
        "canonical_category": row.canonical_category,
        "source_type": row.source_type,
        "external_provider": row.external_provider,
        "external_food_id": row.external_food_id,
        "fdc_id": row.external_food_id,
        "display_name": row.display_name,
        "brand_name": row.brand_name,
        "serving_size": _decimal_str(row.serving_size),
        "serving_unit": row.serving_unit,
        "serving_weight_grams": _decimal_str(row.serving_weight_grams),
        "protein": _decimal_str(row.protein),
        "carbs": _decimal_str(row.carbs),
        "fats": _decimal_str(row.fats),
        "calories": _decimal_str(row.calories),
        "active": row.active,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def _normalized_usda_payload(row: dict) -> dict:
    return {
        "external_provider": "usda",
        "fdc_id": row.get("fdc_id"),
        "display_name": row.get("display_name"),
        "brand_name": row.get("brand_name"),
        "data_type": row.get("data_type"),
        "serving_size": _decimal_str(row.get("serving_size")),
        "serving_unit": row.get("serving_unit"),
        "serving_weight_grams": _decimal_str(row.get("serving_weight_grams")),
        "protein": _decimal_str(row.get("protein")),
        "carbs": _decimal_str(row.get("carbs")),
        "fats": _decimal_str(row.get("fats")),
        "calories": _decimal_str(row.get("calories")),
    }


def _supported_canonical_categories() -> set[str]:
    supported = get_supported_combo_slot_values()
    return {value for values in supported.values() for value in values if value and value != "-"}


def _normalize_supported_category(value):
    canonical = canonical_standard_name(value)
    if canonical not in _supported_canonical_categories():
        return None
    return canonical


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def client_food_overrides(request):
    auth_error = require_client(request)
    if auth_error:
        return auth_error

    rows = ClientFoodOverride.objects.filter(user=request.user, active=True).order_by("canonical_category")
    return ok({"food_overrides": [_override_payload(row) for row in rows]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def client_usda_food_search(request):
    auth_error = require_client(request)
    if auth_error:
        return auth_error

    payload = request.data or {}
    query = str(payload.get("query") or "").strip()
    if not query:
        return error("MISSING_QUERY", "Search query is required.", http_status=400)

    try:
        page = int(payload.get("page") or 1)
        page_size = int(payload.get("page_size") or 20)
    except (TypeError, ValueError):
        return error("INVALID_PAGING", "page and page_size must be integers.", http_status=400)
    data_type = str(payload.get("data_type") or "Branded").strip() or None

    try:
        result = search_foods(query, page=page, page_size=page_size, data_type=data_type)
    except USDAFoodDataError as exc:
        return error("USDA_SEARCH_FAILED", str(exc), http_status=502)

    return ok(
        {
            "usda_foods": [_normalized_usda_payload(row) for row in result["foods"]],
            "page": result["page"],
            "page_size": result["page_size"],
            "total_hits": result["total_hits"],
            "total_pages": result["total_pages"],
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def client_usda_food_detail(request, fdc_id: str):
    auth_error = require_client(request)
    if auth_error:
        return auth_error

    try:
        details = get_food_details(fdc_id)
    except USDAFoodDataError as exc:
        return error("USDA_DETAIL_FAILED", str(exc), http_status=502)

    return ok({"usda_food": _normalized_usda_payload(details)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def client_food_override_save(request):
    auth_error = require_client(request)
    if auth_error:
        return auth_error

    payload = request.data or {}
    canonical_category = _normalize_supported_category(payload.get("canonical_category"))
    if not canonical_category:
        return error("INVALID_CANONICAL_CATEGORY", "canonical_category must be a supported STANDARD combo category.", http_status=400)
    fdc_id = str(payload.get("fdc_id") or payload.get("external_food_id") or "").strip()
    if not fdc_id:
        return error("MISSING_FDC_ID", "USDA fdc_id is required.", http_status=400)

    try:
        details = get_food_details(fdc_id)
    except USDAFoodDataError as exc:
        return error("USDA_DETAIL_FAILED", str(exc), http_status=502)

    with transaction.atomic():
        ClientFoodOverride.objects.filter(
            user=request.user,
            canonical_category=canonical_category,
            active=True,
        ).update(active=False)
        row = ClientFoodOverride.objects.create(
            user=request.user,
            canonical_category=canonical_category,
            source_type=ClientFoodOverride.SOURCE_TYPE_USDA,
            external_provider="usda",
            external_food_id=details["fdc_id"] or fdc_id,
            display_name=details["display_name"] or f"USDA {fdc_id}",
            brand_name=details["brand_name"] or "",
            serving_size=details["serving_size"] or 0,
            serving_unit=details["serving_unit"] or "",
            serving_weight_grams=details["serving_weight_grams"] or 0,
            protein=details["protein"] or 0,
            carbs=details["carbs"] or 0,
            fats=details["fats"] or 0,
            calories=details["calories"] or 0,
            raw_payload=details["raw_payload"] or {},
            active=True,
        )

    return ok({"food_override": _override_payload(row)})


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def client_food_override_delete(request, override_id: int):
    auth_error = require_client(request)
    if auth_error:
        return auth_error

    updated = ClientFoodOverride.objects.filter(user=request.user, id=override_id, active=True).update(active=False)
    if not updated:
        return error("OVERRIDE_NOT_FOUND", "Food override not found.", http_status=404)
    return ok({"deleted": True, "id": override_id})
