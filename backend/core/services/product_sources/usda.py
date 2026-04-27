from __future__ import annotations

from typing import Any

from core.services.usda_fooddata import get_food_details, search_foods


PROVIDER = "usda"


def normalize_usda_product(row: dict[str, Any]) -> dict[str, Any]:
    fdc_id = row.get("fdc_id") or row.get("external_food_id") or ""
    return {
        "provider": PROVIDER,
        "external_provider": PROVIDER,
        "provider_product_id": fdc_id,
        "external_food_id": fdc_id,
        "fdc_id": fdc_id,
        "barcode": row.get("barcode") or "",
        "name": row.get("display_name") or fdc_id,
        "display_name": row.get("display_name") or fdc_id,
        "brand": row.get("brand_name") or "",
        "brand_name": row.get("brand_name") or "",
        "data_type": row.get("data_type") or "",
        "serving_size": row.get("serving_size") or 0,
        "serving_unit": row.get("serving_unit") or "",
        "serving_weight_grams": row.get("serving_weight_grams") or 0,
        "protein": row.get("protein") or 0,
        "carbs": row.get("carbs") or 0,
        "fats": row.get("fats") or 0,
        "calories": row.get("calories") or 0,
        "image_url": "",
        "ingredients": "",
        "preparation_state": "as_packaged" if row.get("data_type") == "Branded" else "unknown",
        "measurement_basis_label": "As packaged" if row.get("data_type") == "Branded" else "Measurement basis not specified",
        "raw_payload": row.get("raw_payload") or row,
    }


def search_products(query: str, *, page: int = 1, page_size: int = 12, data_type: str | None = "Branded"):
    result = search_foods(query, page=page, page_size=page_size, data_type=data_type)
    return {
        **result,
        "foods": [normalize_usda_product(row) for row in result.get("foods", [])],
    }


def get_product(product_id: str | int):
    return normalize_usda_product(get_food_details(product_id))
