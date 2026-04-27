from __future__ import annotations

from typing import Any
import logging

from core.services.product_sources import open_food_facts, usda
from core.services.product_sources.open_food_facts import OpenFoodFactsError
from core.services.usda_fooddata import USDAFoodDataError


SUPPORTED_PRODUCT_PROVIDERS = {"usda", "open_food_facts"}
logger = logging.getLogger(__name__)


class ProductSearchError(RuntimeError):
    pass


def _provider_key(value: Any) -> str:
    key = str(value or "").strip().lower()
    aliases = {
        "off": "open_food_facts",
        "openfoodfacts": "open_food_facts",
        "open-food-facts": "open_food_facts",
        "fdc": "usda",
    }
    return aliases.get(key, key)


def normalize_product_payload(row: dict[str, Any]) -> dict[str, Any]:
    provider = _provider_key(row.get("provider") or row.get("external_provider"))
    provider_product_id = str(row.get("provider_product_id") or row.get("external_food_id") or row.get("fdc_id") or "").strip()
    return {
        "provider": provider,
        "external_provider": provider,
        "provider_product_id": provider_product_id,
        "external_food_id": provider_product_id,
        "fdc_id": row.get("fdc_id") if provider == "usda" else "",
        "barcode": str(row.get("barcode") or "").strip(),
        "name": row.get("name") or row.get("display_name") or provider_product_id,
        "display_name": row.get("display_name") or row.get("name") or provider_product_id,
        "brand": row.get("brand") or row.get("brand_name") or "",
        "brand_name": row.get("brand_name") or row.get("brand") or "",
        "data_type": row.get("data_type") or "",
        "serving_size": row.get("serving_size") or 0,
        "serving_unit": row.get("serving_unit") or "",
        "serving_weight_grams": row.get("serving_weight_grams") or 0,
        "protein": row.get("protein") or 0,
        "carbs": row.get("carbs") or 0,
        "fats": row.get("fats") or 0,
        "calories": row.get("calories") or 0,
        "image_url": row.get("image_url") or "",
        "ingredients": row.get("ingredients") or "",
        "preparation_state": row.get("preparation_state") or "as_packaged",
        "measurement_basis_label": row.get("measurement_basis_label") or "As packaged",
        "raw_payload": row.get("raw_payload") or row,
    }


def search_products(
    query: str,
    *,
    page: int = 1,
    page_size: int = 12,
    providers: list[str] | None = None,
) -> dict[str, Any]:
    selected = [_provider_key(provider) for provider in (providers or ["open_food_facts", "usda"])]
    foods = []
    errors = {}
    per_provider_size = max(1, min(int(page_size or 12), 24))

    if "open_food_facts" in selected:
        try:
            foods.extend(open_food_facts.search_products(query, page=page, page_size=per_provider_size)["foods"])
        except OpenFoodFactsError as exc:
            errors["open_food_facts"] = str(exc)

    if "usda" in selected:
        try:
            foods.extend(usda.search_products(query, page=page, page_size=per_provider_size)["foods"])
        except USDAFoodDataError as exc:
            errors["usda"] = str(exc)

    if not foods and errors and all(provider in errors for provider in selected):
        raise ProductSearchError("; ".join(f"{key}: {value}" for key, value in errors.items()))

    return {
        "foods": [normalize_product_payload(row) for row in foods],
        "page": page,
        "page_size": page_size,
        "providers": selected,
        "errors": errors,
    }


def lookup_barcode(barcode: str, *, providers: list[str] | None = None) -> dict[str, Any] | None:
    selected = [_provider_key(provider) for provider in (providers or ["open_food_facts"])]
    logger.info("Product barcode lookup requested: barcode=%s providers=%s", barcode, selected)
    errors = {}
    if "open_food_facts" in selected:
        try:
            product = open_food_facts.get_product_by_barcode(barcode)
            if product:
                normalized = normalize_product_payload(product)
                logger.info(
                    "Product barcode lookup matched: barcode=%s provider=%s product_id=%s",
                    barcode,
                    normalized.get("provider"),
                    normalized.get("provider_product_id"),
                )
                return normalized
        except OpenFoodFactsError as exc:
            errors["open_food_facts"] = str(exc)
    if errors:
        raise ProductSearchError("; ".join(f"{key}: {value}" for key, value in errors.items()))
    logger.info("Product barcode lookup not found: barcode=%s providers=%s", barcode, selected)
    return None


def get_product_details(provider: str, product_id: str):
    key = _provider_key(provider)
    if key == "usda":
        return normalize_product_payload(usda.get_product(product_id))
    if key == "open_food_facts":
        product = open_food_facts.get_product_by_barcode(product_id)
        if not product:
            raise ProductSearchError("Open Food Facts product not found.")
        return normalize_product_payload(product)
    raise ProductSearchError(f"Unsupported product provider: {provider}")
