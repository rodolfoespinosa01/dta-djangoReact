from __future__ import annotations

from typing import Any

import requests
from django.conf import settings


class USDAFoodDataError(RuntimeError):
    pass


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _brand_label(row: dict[str, Any]) -> str:
    brand_owner = _clean(row.get("brandOwner"))
    brand_name = _clean(row.get("brandName"))
    description = _clean(row.get("description"))
    if brand_owner and brand_name:
        return f"{brand_owner} ({brand_name})"
    return brand_owner or brand_name or description


def _request_usda_search(
    url: str,
    *,
    api_key: str,
    query: str,
    page_size: int,
    page_number: int,
    timeout_seconds: int,
    branded_only: bool,
) -> dict[str, Any]:
    params = {
        "api_key": api_key,
        "query": query,
        "pageSize": page_size,
        "pageNumber": page_number,
    }
    if branded_only:
        params["dataType"] = "Branded"

    # Try GET first, then POST fallback (USDA supports both for search).
    try:
        response = requests.get(url, params=params, timeout=timeout_seconds)
        response.raise_for_status()
        return response.json() or {}
    except Exception:
        try:
            post_params = {"api_key": api_key}
            body: dict[str, Any] = {
                "query": query,
                "pageSize": page_size,
                "pageNumber": page_number,
            }
            if branded_only:
                body["dataType"] = ["Branded"]
            response = requests.post(url, params=post_params, json=body, timeout=timeout_seconds)
            response.raise_for_status()
            return response.json() or {}
        except Exception as exc:
            raise USDAFoodDataError(f"Unable to fetch USDA brand data: {exc}") from exc


def search_branded_food_options(food_name: str, *, limit: int = 30) -> list[dict[str, str]]:
    """
    Returns branded USDA matches for a base food label (e.g. "Chicken Breast").
    Output shape is intentionally UI-friendly and separate from macro calculations.
    """
    query = _clean(food_name)
    if not query:
        return []

    api_key = _clean(getattr(settings, "USDA_FOODDATA_API_KEY", "")) or "DEMO_KEY"
    base_url = _clean(getattr(settings, "USDA_FOODDATA_BASE_URL", "https://api.nal.usda.gov/fdc/v1")).rstrip("/")
    timeout_seconds = int(getattr(settings, "USDA_FOODDATA_TIMEOUT_SECONDS", 8) or 8)
    target = min(max(int(limit or 30), 1), 100)

    url = f"{base_url}/foods/search"
    page_number = 1
    page_size = min(max(target, 10), 50)
    collected: list[dict[str, str]] = []
    seen: set[str] = set()

    def _collect_from_payload(payload: dict[str, Any], *, enforce_branded: bool) -> None:
        rows = list(payload.get("foods") or [])
        for row in rows:
            if enforce_branded:
                data_type = _clean(row.get("dataType") or row.get("data_type")).lower()
                if data_type and "branded" not in data_type:
                    continue
            label = _brand_label(row)
            if not label:
                continue
            key = label.lower()
            if key in seen:
                continue
            seen.add(key)
            collected.append(
                {
                    "brand": label,
                    "description": _clean(row.get("description")),
                    "fdc_id": _clean(row.get("fdcId")),
                }
            )
            if len(collected) >= target:
                break

    # Pass 1: branded only
    while len(collected) < target and page_number <= 3:
        payload = _request_usda_search(
            url,
            api_key=api_key,
            query=query,
            page_size=page_size,
            page_number=page_number,
            timeout_seconds=timeout_seconds,
            branded_only=True,
        )
        _collect_from_payload(payload, enforce_branded=True)
        rows = list(payload.get("foods") or [])
        if not rows:
            break
        total_pages = int(payload.get("totalPages") or 0)
        if total_pages and page_number >= total_pages:
            break
        page_number += 1

    # Pass 2 fallback: broaden search when branded-only yields too little.
    if len(collected) < max(5, min(target, 10)):
        page_number = 1
        while len(collected) < target and page_number <= 2:
            payload = _request_usda_search(
                url,
                api_key=api_key,
                query=query,
                page_size=page_size,
                page_number=page_number,
                timeout_seconds=timeout_seconds,
                branded_only=False,
            )
            _collect_from_payload(payload, enforce_branded=False)
            rows = list(payload.get("foods") or [])
            if not rows:
                break
            total_pages = int(payload.get("totalPages") or 0)
            if total_pages and page_number >= total_pages:
                break
            page_number += 1

    return collected
