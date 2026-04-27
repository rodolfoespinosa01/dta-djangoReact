from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

import requests
from django.conf import settings


class USDAFoodDataError(RuntimeError):
    pass


OZ_TO_GRAMS = Decimal("28.3495")
NUTRIENT_KEYS = {
    "protein": {"ids": {"1003"}, "numbers": {"203"}, "names": {"protein"}},
    "carbs": {"ids": {"1005"}, "numbers": {"205"}, "names": {"carbohydrate, by difference", "carbohydrate"}},
    "fats": {"ids": {"1004"}, "numbers": {"204"}, "names": {"total lipid (fat)", "total fat", "fat"}},
    "calories": {"ids": {"1008"}, "numbers": {"208"}, "names": {"energy", "calories"}},
}
LABEL_NUTRIENT_KEYS = {
    "protein": ("protein",),
    "carbs": ("carbohydrates", "carbs"),
    "fats": ("fat", "fats"),
    "calories": ("calories",),
}


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _decimal(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def _q(value: Decimal, places: str = "0.00001") -> Decimal:
    return value.quantize(Decimal(places), rounding=ROUND_HALF_UP)


def _api_key() -> str:
    return _clean(getattr(settings, "USDA_FDC_API_KEY", "")) or _clean(getattr(settings, "USDA_FOODDATA_API_KEY", "")) or "DEMO_KEY"


def _base_url() -> str:
    return _clean(getattr(settings, "USDA_FOODDATA_BASE_URL", "https://api.nal.usda.gov/fdc/v1")).rstrip("/")


def _timeout_seconds() -> int:
    try:
        return int(getattr(settings, "USDA_FOODDATA_TIMEOUT_SECONDS", 8) or 8)
    except (TypeError, ValueError):
        return 8


def _brand_name(row: dict[str, Any]) -> str:
    return _clean(row.get("brandOwner")) or _clean(row.get("brandName")) or _clean(row.get("brand_name"))


def _display_name(row: dict[str, Any]) -> str:
    brand = _brand_name(row)
    description = _clean(row.get("description")) or _clean(row.get("lowercaseDescription"))
    if brand and description and brand.lower() not in description.lower():
        return f"{brand} - {description}"
    return description or brand or _clean(row.get("fdcId"))


def _request(method: str, path: str, *, params: dict[str, Any] | None = None, json: dict[str, Any] | None = None) -> dict[str, Any]:
    url = f"{_base_url()}/{path.lstrip('/')}"
    query_params = {"api_key": _api_key(), **(params or {})}
    try:
        response = requests.request(
            method,
            url,
            params=query_params,
            json=json,
            timeout=_timeout_seconds(),
        )
        response.raise_for_status()
        return response.json() or {}
    except Exception as exc:
        raise USDAFoodDataError(f"Unable to fetch USDA FoodData Central data: {exc}") from exc


def _label_nutrient_value(payload: dict[str, Any], key: str) -> Decimal:
    label = payload.get("labelNutrients") or {}
    if isinstance(label, dict):
        for label_key in LABEL_NUTRIENT_KEYS.get(key, (key,)):
            row = label.get(label_key)
            if isinstance(row, dict):
                return _decimal(row.get("value"))
    return Decimal("0")


def _food_nutrients(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("foodNutrients") or payload.get("food_nutrients") or []
    return rows if isinstance(rows, list) else []


def _nutrient_value(payload: dict[str, Any], key: str) -> Decimal:
    label_value = _label_nutrient_value(payload, key)
    if label_value > 0:
        return label_value

    spec = NUTRIENT_KEYS[key]
    for row in _food_nutrients(payload):
        nutrient = row.get("nutrient") if isinstance(row.get("nutrient"), dict) else {}
        nutrient_id = _clean(row.get("nutrientId") or nutrient.get("id"))
        nutrient_number = _clean(row.get("nutrientNumber") or nutrient.get("number"))
        nutrient_name = _clean(row.get("nutrientName") or nutrient.get("name")).lower()
        if (
            nutrient_id in spec["ids"]
            or nutrient_number in spec["numbers"]
            or nutrient_name in spec["names"]
        ):
            return _decimal(row.get("value") if "value" in row else row.get("amount"))
    return Decimal("0")


def _serving_size(payload: dict[str, Any]) -> Decimal:
    return _decimal(payload.get("servingSize") or payload.get("serving_size"))


def _serving_unit(payload: dict[str, Any]) -> str:
    return _clean(payload.get("servingSizeUnit") or payload.get("serving_size_unit"))


def _serving_weight_grams(payload: dict[str, Any]) -> Decimal:
    direct = _decimal(payload.get("servingWeightGrams") or payload.get("serving_weight_grams"))
    if direct > 0:
        return direct
    size = _serving_size(payload)
    unit = _serving_unit(payload).lower()
    if size > 0 and unit in {"g", "gram", "grams", "ml", "milliliter", "milliliters"}:
        return size
    return Decimal("0")


def _per_oz_from_detail(payload: dict[str, Any], key: str) -> Decimal:
    value = _nutrient_value(payload, key)
    if value <= 0:
        return Decimal("0")
    serving_grams = _serving_weight_grams(payload)
    has_label = _label_nutrient_value(payload, key) > 0
    if has_label and serving_grams > 0:
        return _q(value / serving_grams * OZ_TO_GRAMS)
    return _q(value / Decimal("100") * OZ_TO_GRAMS)


def normalize_food(payload: dict[str, Any]) -> dict[str, Any]:
    serving_size = _serving_size(payload)
    serving_unit = _serving_unit(payload)
    serving_weight_grams = _serving_weight_grams(payload)
    return {
        "external_provider": "usda",
        "fdc_id": _clean(payload.get("fdcId") or payload.get("fdc_id")),
        "barcode": _clean(payload.get("gtinUpc") or payload.get("gtin_upc") or payload.get("upc") or payload.get("barcode")),
        "display_name": _display_name(payload),
        "brand_name": _brand_name(payload),
        "data_type": _clean(payload.get("dataType") or payload.get("data_type")),
        "serving_size": _q(serving_size, "0.0001"),
        "serving_unit": serving_unit,
        "serving_weight_grams": _q(serving_weight_grams, "0.0001"),
        "protein": _per_oz_from_detail(payload, "protein"),
        "carbs": _per_oz_from_detail(payload, "carbs"),
        "fats": _per_oz_from_detail(payload, "fats"),
        "calories": _per_oz_from_detail(payload, "calories"),
        "raw_payload": payload,
    }


def search_foods(
    query: str,
    *,
    page: int = 1,
    page_size: int = 25,
    data_type: str | None = "Branded",
) -> dict[str, Any]:
    q = _clean(query)
    if not q:
        return {"foods": [], "page": 1, "page_size": page_size, "total_hits": 0, "total_pages": 0}

    safe_page = max(int(page or 1), 1)
    safe_size = min(max(int(page_size or 25), 1), 50)
    body: dict[str, Any] = {
        "query": q,
        "pageSize": safe_size,
        "pageNumber": safe_page,
    }
    if data_type:
        body["dataType"] = [data_type]

    payload = _request("POST", "foods/search", json=body)
    foods = [normalize_food(row) for row in list(payload.get("foods") or []) if isinstance(row, dict)]
    return {
        "foods": foods,
        "page": int(payload.get("currentPage") or safe_page),
        "page_size": safe_size,
        "total_hits": int(payload.get("totalHits") or 0),
        "total_pages": int(payload.get("totalPages") or 0),
    }


def get_food_details(fdc_id: str | int) -> dict[str, Any]:
    external_id = _clean(fdc_id)
    if not external_id:
        raise USDAFoodDataError("USDA fdc_id is required.")
    payload = _request("GET", f"food/{external_id}")
    return normalize_food(payload)


def search_branded_food_options(food_name: str, *, limit: int = 30) -> list[dict[str, str]]:
    """
    Backward-compatible wrapper used by older UI surfaces.
    """
    result = search_foods(food_name, page=1, page_size=limit, data_type="Branded")
    return [
        {
            "brand": row.get("brand_name") or row.get("display_name") or "",
            "description": row.get("display_name") or "",
            "fdc_id": row.get("fdc_id") or "",
        }
        for row in result["foods"]
    ]
