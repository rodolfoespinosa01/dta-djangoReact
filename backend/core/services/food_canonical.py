from __future__ import annotations

STANDARD_SUFFIX = " STANDARD"
PLACEHOLDER = "-"


def normalize_food_token(value: str | None) -> str:
    normalized = str(value or "").strip()
    return normalized or PLACEHOLDER


def canonical_standard_name(value: str | None) -> str:
    normalized = normalize_food_token(value)
    if normalized == PLACEHOLDER:
        return PLACEHOLDER
    if normalized.upper().endswith(STANDARD_SUFFIX):
        return normalized
    return f"{normalized}{STANDARD_SUFFIX}"
