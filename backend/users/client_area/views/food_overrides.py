from decimal import Decimal

from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from core.services.food_canonical import canonical_standard_name
from core.services.meal_combo_lookup import get_supported_combo_slot_values
from core.services.product_search import ProductSearchError, get_product_details, lookup_barcode, search_products
from core.services.usda_fooddata import USDAFoodDataError, get_food_details, search_foods
from users.client_area.models import ClientFoodOverride, ProductImageSubmission
from users.client_area.views.api_contract import error, ok, require_client


def _decimal_str(value):
    if isinstance(value, Decimal):
        return str(value)
    return str(value or "0")


def _submission_image_url(request, submission):
    if not submission or not submission.image:
        return ""
    return request.build_absolute_uri(submission.image.url)


def _product_keys(product):
    provider = str(product.get("provider") or product.get("external_provider") or "").strip()
    provider_product_id = str(product.get("provider_product_id") or product.get("external_food_id") or product.get("fdc_id") or "").strip()
    barcode = str(product.get("barcode") or "").strip()
    return provider, provider_product_id, barcode


def _submission_for_product(product, *, user=None, status=None):
    provider, provider_product_id, barcode = _product_keys(product)
    qs = ProductImageSubmission.objects.all()
    if status:
        qs = qs.filter(status=status)
    if user is not None:
        qs = qs.filter(submitted_by=user)
    provider_qs = qs.none()
    if provider and provider_product_id:
        provider_qs = qs.filter(provider=provider, provider_product_id=provider_product_id)
    barcode_qs = qs.none()
    if barcode:
        barcode_qs = qs.filter(barcode=barcode)
    return (provider_qs | barcode_qs).order_by("-updated_at").first()


def _apply_product_image_state(request, product):
    approved = _submission_for_product(product, status=ProductImageSubmission.Status.APPROVED)
    pending = _submission_for_product(
        product,
        user=request.user,
        status=ProductImageSubmission.Status.PENDING,
    )
    enriched = dict(product)
    provider_image_url = enriched.get("image_url") or ""
    enriched["provider_image_url"] = provider_image_url
    if approved:
        enriched["image_url"] = _submission_image_url(request, approved)
        enriched["image_source"] = "approved_local"
        enriched["approved_image_id"] = approved.id
    else:
        enriched["image_url"] = provider_image_url
        enriched["image_source"] = "provider" if provider_image_url else ""
    if pending:
        enriched["image_submission_status"] = pending.status
        enriched["image_submission_id"] = pending.id
    return enriched


def _override_payload(row: ClientFoodOverride) -> dict:
    return {
        "id": row.id,
        "canonical_category": row.canonical_category,
        "source_type": row.source_type,
        "external_provider": row.external_provider,
        "external_food_id": row.external_food_id,
        "fdc_id": row.external_food_id,
        "barcode": row.barcode,
        "provider": row.external_provider,
        "provider_product_id": row.external_food_id,
        "image_url": row.image_url,
        "display_name": row.display_name,
        "name": row.display_name,
        "brand_name": row.brand_name,
        "brand": row.brand_name,
        "ingredients": row.ingredients,
        "serving_size": _decimal_str(row.serving_size),
        "serving_unit": row.serving_unit,
        "serving_weight_grams": _decimal_str(row.serving_weight_grams),
        "preparation_state": row.preparation_state,
        "measurement_basis_label": row.measurement_basis_label,
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
        "provider": "usda",
        "fdc_id": row.get("fdc_id"),
        "provider_product_id": row.get("fdc_id"),
        "external_food_id": row.get("fdc_id"),
        "barcode": row.get("barcode"),
        "display_name": row.get("display_name"),
        "name": row.get("display_name"),
        "brand_name": row.get("brand_name"),
        "brand": row.get("brand_name"),
        "data_type": row.get("data_type"),
        "serving_size": _decimal_str(row.get("serving_size")),
        "serving_unit": row.get("serving_unit"),
        "serving_weight_grams": _decimal_str(row.get("serving_weight_grams")),
        "protein": _decimal_str(row.get("protein")),
        "carbs": _decimal_str(row.get("carbs")),
        "fats": _decimal_str(row.get("fats")),
        "calories": _decimal_str(row.get("calories")),
        "image_url": row.get("image_url") or "",
        "ingredients": row.get("ingredients") or "",
        "preparation_state": row.get("preparation_state") or "unknown",
        "measurement_basis_label": row.get("measurement_basis_label") or "Measurement basis not specified",
    }


def _normalized_product_payload(row: dict) -> dict:
    provider = row.get("provider") or row.get("external_provider")
    return {
        "provider": provider,
        "external_provider": provider,
        "provider_product_id": row.get("provider_product_id") or row.get("external_food_id") or row.get("fdc_id"),
        "external_food_id": row.get("external_food_id") or row.get("provider_product_id") or row.get("fdc_id"),
        "fdc_id": row.get("fdc_id") or "",
        "barcode": row.get("barcode") or "",
        "display_name": row.get("display_name") or row.get("name"),
        "name": row.get("name") or row.get("display_name"),
        "brand_name": row.get("brand_name") or row.get("brand"),
        "brand": row.get("brand") or row.get("brand_name"),
        "data_type": row.get("data_type") or "",
        "serving_size": _decimal_str(row.get("serving_size")),
        "serving_unit": row.get("serving_unit") or "",
        "serving_weight_grams": _decimal_str(row.get("serving_weight_grams")),
        "protein": _decimal_str(row.get("protein")),
        "carbs": _decimal_str(row.get("carbs")),
        "fats": _decimal_str(row.get("fats")),
        "calories": _decimal_str(row.get("calories")),
        "image_url": row.get("image_url") or "",
        "provider_image_url": row.get("provider_image_url") or "",
        "image_source": row.get("image_source") or "",
        "image_submission_status": row.get("image_submission_status") or "",
        "image_submission_id": row.get("image_submission_id") or None,
        "approved_image_id": row.get("approved_image_id") or None,
        "ingredients": row.get("ingredients") or "",
        "preparation_state": row.get("preparation_state") or "as_packaged",
        "measurement_basis_label": row.get("measurement_basis_label") or "As packaged",
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
def client_product_search(request):
    auth_error = require_client(request)
    if auth_error:
        return auth_error

    payload = request.data or {}
    query = str(payload.get("query") or "").strip()
    if not query:
        return error("MISSING_QUERY", "Search query is required.", http_status=400)
    try:
        page = int(payload.get("page") or 1)
        page_size = int(payload.get("page_size") or 12)
    except (TypeError, ValueError):
        return error("INVALID_PAGING", "page and page_size must be integers.", http_status=400)
    providers = payload.get("providers")
    if not isinstance(providers, list):
        providers = None

    try:
        result = search_products(query, page=page, page_size=page_size, providers=providers)
    except ProductSearchError as exc:
        return error("PRODUCT_SEARCH_FAILED", str(exc), http_status=502)
    return ok(
        {
            "products": [_normalized_product_payload(_apply_product_image_state(request, row)) for row in result["foods"]],
            "provider_errors": result.get("errors") or {},
            "providers": result.get("providers") or [],
            "page": result["page"],
            "page_size": result["page_size"],
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def client_product_barcode_lookup(request):
    auth_error = require_client(request)
    if auth_error:
        return auth_error

    barcode = str((request.data or {}).get("barcode") or "").strip()
    if not barcode:
        return error("MISSING_BARCODE", "Barcode is required.", http_status=400)
    try:
        product = lookup_barcode(barcode)
    except ProductSearchError as exc:
        return error("PRODUCT_LOOKUP_FAILED", str(exc), http_status=502)
    if not product:
        return error("PRODUCT_NOT_FOUND", "Product not found. Add manually or try another search.", http_status=404)
    return ok({"product": _normalized_product_payload(_apply_product_image_state(request, product))})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def client_product_image_submission_upload(request):
    auth_error = require_client(request)
    if auth_error:
        return auth_error

    image = request.FILES.get("image")
    if not image:
        return error("MISSING_IMAGE", "Product image is required.", http_status=400)
    if not str(getattr(image, "content_type", "") or "").lower().startswith("image/"):
        return error("INVALID_IMAGE", "Uploaded file must be an image.", http_status=400)

    provider = str(request.data.get("provider") or request.data.get("external_provider") or "").strip()
    provider_product_id = str(
        request.data.get("provider_product_id")
        or request.data.get("external_food_id")
        or request.data.get("fdc_id")
        or ""
    ).strip()
    barcode = str(request.data.get("barcode") or "").strip()
    if not provider or not provider_product_id:
        return error("MISSING_PRODUCT_ID", "provider and provider_product_id are required.", http_status=400)

    submission = ProductImageSubmission.objects.create(
        submitted_by=request.user,
        provider=provider,
        provider_product_id=provider_product_id,
        barcode=barcode,
        product_name=str(request.data.get("product_name") or request.data.get("display_name") or "").strip(),
        brand=str(request.data.get("brand") or request.data.get("brand_name") or "").strip(),
        image=image,
        status=ProductImageSubmission.Status.PENDING,
    )
    return ok(
        {
            "image_submission": {
                "id": submission.id,
                "status": submission.status,
                "provider": submission.provider,
                "provider_product_id": submission.provider_product_id,
                "barcode": submission.barcode,
                "image_url": _submission_image_url(request, submission),
                "message": "Image submitted for review.",
            }
        }
    )


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
    provider = str(payload.get("provider") or payload.get("external_provider") or "usda").strip() or "usda"
    product_id = str(
        payload.get("provider_product_id")
        or payload.get("external_food_id")
        or payload.get("fdc_id")
        or payload.get("barcode")
        or ""
    ).strip()
    if not product_id:
        return error("MISSING_PRODUCT_ID", "provider_product_id is required.", http_status=400)

    try:
        details = get_product_details(provider, product_id)
    except (ProductSearchError, USDAFoodDataError) as exc:
        return error("PRODUCT_DETAIL_FAILED", str(exc), http_status=502)

    with transaction.atomic():
        ClientFoodOverride.objects.filter(
            user=request.user,
            canonical_category=canonical_category,
            active=True,
        ).update(active=False)
        enriched_details = _apply_product_image_state(request, details)
        row = ClientFoodOverride.objects.create(
            user=request.user,
            canonical_category=canonical_category,
            source_type=details["provider"],
            external_provider=details["provider"],
            external_food_id=details["provider_product_id"] or product_id,
            barcode=details.get("barcode") or "",
            image_url=enriched_details.get("image_url") or "",
            display_name=details["display_name"] or f"{details['provider']} {product_id}",
            brand_name=details["brand_name"] or "",
            ingredients=details.get("ingredients") or "",
            serving_size=details["serving_size"] or 0,
            serving_unit=details["serving_unit"] or "",
            serving_weight_grams=details["serving_weight_grams"] or 0,
            preparation_state=details.get("preparation_state") or ClientFoodOverride.PreparationState.AS_PACKAGED,
            measurement_basis_label=details.get("measurement_basis_label") or "As packaged",
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
