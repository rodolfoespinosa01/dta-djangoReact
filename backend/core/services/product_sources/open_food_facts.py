from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

import requests
from django.conf import settings
from requests import HTTPError


class OpenFoodFactsError(RuntimeError):
    pass


OZ_TO_GRAMS = Decimal("28.3495")
PROVIDER = "open_food_facts"


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


def _base_url() -> str:
    return _clean(getattr(settings, "OPEN_FOOD_FACTS_BASE_URL", "https://world.openfoodfacts.org")).rstrip("/")


def _timeout_seconds() -> int:
    try:
        return int(getattr(settings, "OPEN_FOOD_FACTS_TIMEOUT_SECONDS", 8) or 8)
    except (TypeError, ValueError):
        return 8


def _user_agent() -> str:
    return _clean(
        getattr(
            settings,
            "OPEN_FOOD_FACTS_USER_AGENT",
            "DTA-Diet-Generator/1.0 (support@dtameals.com)",
        )
    )


def _request(path: str, *, params: dict[str, Any] | None = None, allow_404: bool = False) -> dict[str, Any]:
    url = f"{_base_url()}/{path.lstrip('/')}"
    try:
        response = requests.get(
            url,
            params=params or {},
            headers={"User-Agent": _user_agent()},
            timeout=_timeout_seconds(),
        )
        if allow_404 and response.status_code == 404:
            return {"status": 0}
        response.raise_for_status()
        return response.json() or {}
    except HTTPError as exc:
        if allow_404 and getattr(exc.response, "status_code", None) == 404:
            return {"status": 0}
        raise OpenFoodFactsError(f"Unable to fetch Open Food Facts data: {exc}") from exc
    except Exception as exc:
        raise OpenFoodFactsError(f"Unable to fetch Open Food Facts data: {exc}") from exc


def _nutriment(product: dict[str, Any], *keys: str) -> Decimal:
    nutriments = product.get("nutriments") if isinstance(product.get("nutriments"), dict) else {}
    for key in keys:
        value = _decimal(nutriments.get(key))
        if value > 0:
            return value
    return Decimal("0")


def _per_oz_from_100g(product: dict[str, Any], *keys: str) -> Decimal:
    value = _nutriment(product, *keys)
    if value <= 0:
        return Decimal("0")
    return _q(value / Decimal("100") * OZ_TO_GRAMS)


def _product_name(product: dict[str, Any]) -> str:
    return (
        _clean(product.get("product_name"))
        or _clean(product.get("product_name_en"))
        or _clean(product.get("generic_name"))
        or _clean(product.get("code"))
    )


def _brand_name(product: dict[str, Any]) -> str:
    brands = product.get("brands")
    if isinstance(brands, str):
        return _clean(brands.split(",")[0])
    return _clean(product.get("brands_tags", [""])[0] if isinstance(product.get("brands_tags"), list) else "")


def _image_url(product: dict[str, Any]) -> str:
    return (
        _clean(product.get("image_front_url"))
        or _clean(product.get("image_url"))
        or _clean(product.get("selected_images", {}).get("front", {}).get("display", {}).get("en"))
    )


def normalize_product(product: dict[str, Any]) -> dict[str, Any]:
    barcode = _clean(product.get("code") or product.get("_id") or product.get("barcode"))
    serving_size = _decimal(product.get("serving_quantity"))
    serving_label = _clean(product.get("serving_size"))
    return {
        "provider": PROVIDER,
        "external_provider": PROVIDER,
        "provider_product_id": barcode,
        "external_food_id": barcode,
        "barcode": barcode,
        "name": _product_name(product),
        "display_name": _product_name(product),
        "brand": _brand_name(product),
        "brand_name": _brand_name(product),
        "serving_size": _q(serving_size, "0.0001"),
        "serving_unit": serving_label,
        "serving_weight_grams": _q(serving_size, "0.0001"),
        "protein": _per_oz_from_100g(product, "proteins_100g", "proteins"),
        "carbs": _per_oz_from_100g(product, "carbohydrates_100g", "carbohydrates"),
        "fats": _per_oz_from_100g(product, "fat_100g", "fat"),
        "calories": _per_oz_from_100g(product, "energy-kcal_100g", "energy-kcal"),
        "image_url": _image_url(product),
        "ingredients": _clean(product.get("ingredients_text") or product.get("ingredients_text_en")),
        "preparation_state": "as_packaged",
        "measurement_basis_label": "As packaged",
        "raw_payload": product,
    }


def search_products(query: str, *, page: int = 1, page_size: int = 12) -> dict[str, Any]:
    q = _clean(query)
    if not q:
        return {"foods": [], "page": 1, "page_size": page_size, "total_hits": 0, "total_pages": 0}
    safe_page = max(int(page or 1), 1)
    safe_size = min(max(int(page_size or 12), 1), 24)
    payload = _request(
        "api/v2/search",
        params={
            "search_terms": q,
            "page": safe_page,
            "page_size": safe_size,
            "fields": ",".join(
                [
                    "code",
                    "product_name",
                    "product_name_en",
                    "generic_name",
                    "brands",
                    "serving_size",
                    "serving_quantity",
                    "nutriments",
                    "image_url",
                    "image_front_url",
                    "ingredients_text",
                    "ingredients_text_en",
                ]
            ),
        },
    )
    products = payload.get("products") if isinstance(payload.get("products"), list) else []
    return {
        "foods": [normalize_product(row) for row in products if isinstance(row, dict)],
        "page": int(payload.get("page") or safe_page),
        "page_size": safe_size,
        "total_hits": int(payload.get("count") or 0),
        "total_pages": int(payload.get("page_count") or 0),
    }


def get_product_by_barcode(barcode: str) -> dict[str, Any] | None:
    clean_barcode = "".join(ch for ch in _clean(barcode) if ch.isdigit())
    if not clean_barcode:
        raise OpenFoodFactsError("Barcode is required.")
    payload = _request(
        f"api/v2/product/{clean_barcode}",
        params={
            "fields": ",".join(
                [
                    "code",
                    "product_name",
                    "product_name_en",
                    "generic_name",
                    "brands",
                    "serving_size",
                    "serving_quantity",
                    "nutriments",
                    "image_url",
                    "image_front_url",
                    "ingredients_text",
                    "ingredients_text_en",
                ]
            )
        },
        allow_404=True,
    )
    if int(payload.get("status") or 0) != 1:
        payload = _request(
            f"api/v0/product/{clean_barcode}.json",
            params={
                "fields": ",".join(
                    [
                        "code",
                        "product_name",
                        "product_name_en",
                        "generic_name",
                        "brands",
                        "serving_size",
                        "serving_quantity",
                        "nutriments",
                        "image_url",
                        "image_front_url",
                        "ingredients_text",
                        "ingredients_text_en",
                    ]
                )
            },
            allow_404=True,
        )
    if int(payload.get("status") or 0) != 1:
        return None
    product = payload.get("product") if isinstance(payload.get("product"), dict) else {}
    return normalize_product(product)
