from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import requests


DEFAULT_IDEAS_PER_MEAL = 3
MAX_IDEAS_PER_MEAL = 5
MIN_SLOT_AMOUNT_OZ = 0.05


@dataclass
class ProviderResult:
    provider: str
    model: str
    raw_text: str


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_ideas_per_meal(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = DEFAULT_IDEAS_PER_MEAL
    return max(1, min(parsed, MAX_IDEAS_PER_MEAL))


def _usable_slots(meal: dict[str, Any]) -> list[dict[str, Any]]:
    slots = []
    for slot_key, slot in (meal.get("slots") or {}).items():
        name = str((slot or {}).get("name") or "").strip()
        amount_oz = float((slot or {}).get("amount_oz") or 0)
        if not name or name == "-" or amount_oz < MIN_SLOT_AMOUNT_OZ:
            continue
        slots.append(
            {
                "slot_key": slot_key,
                "name": name,
                "amount_oz": round(amount_oz, 2),
                "amount_g": round(float((slot or {}).get("amount_g") or 0), 2),
            }
        )
    return slots


def _mock_recipe_ideas_for_meal(meal: dict[str, Any], idea_count: int) -> list[dict[str, Any]]:
    foods = _usable_slots(meal)
    food_names = [row["name"] for row in foods] or ["meal ingredients"]
    lead = food_names[0]
    secondary = food_names[1] if len(food_names) > 1 else None
    joined_foods = ", ".join(food_names)

    templates = [
        {
            "title": f"{lead} Skillet Bowl",
            "prep_style": "Skillet + bowl assembly",
            "cook_time_minutes": 18,
            "seasoning": [
                "garlic powder",
                "black pepper",
                "paprika",
                "sea salt",
                "lemon juice",
            ],
            "steps": [
                "Cook the protein with dry seasonings in a hot skillet.",
                "Warm carbs separately and keep textures distinct.",
                "Assemble all foods in one bowl and finish with lemon juice.",
            ],
            "meal_prep_tip": "Prep 2-3 portions and keep wet ingredients separate until serving.",
            "variation_options": [
                "Swap lemon juice for lime juice.",
                "Use smoked paprika instead of regular paprika.",
                "Finish with chopped parsley for a fresher profile.",
            ],
        },
        {
            "title": f"{lead} {secondary or 'Balanced'} Plate",
            "prep_style": "Tray + pan meal prep",
            "cook_time_minutes": 25,
            "seasoning": [
                "onion powder",
                "oregano",
                "chili flakes (optional)",
                "salt",
            ],
            "steps": [
                "Season the main protein and roast or pan-cook until done.",
                "Batch-cook carb sources and portion by weight.",
                "Add fats at the end for texture and better storage.",
            ],
            "meal_prep_tip": "Weigh each component after cooking so portions still match the plan.",
            "variation_options": [
                "Make it herb-forward with oregano + thyme.",
                "Make it spicy with chili flakes + black pepper.",
                "Make it savory with onion powder + garlic powder.",
            ],
        },
        {
            "title": f"{lead} Seasoned Prep Combo",
            "prep_style": "Simple meal-prep containers",
            "cook_time_minutes": 15,
            "seasoning": [
                "cumin",
                "smoked paprika",
                "garlic powder",
                "lime juice",
            ],
            "steps": [
                "Cook each component with minimal oil and consistent seasoning.",
                "Layer foods in containers to preserve texture.",
                "Reheat proteins/carbs, then add fats and bright acids before eating.",
            ],
            "meal_prep_tip": "Use one seasoning blend across the batch to reduce prep time.",
            "variation_options": [
                "Use cumin + lime for a taco-style profile.",
                "Use paprika + garlic for a smoky profile.",
                "Use oregano + pepper for a simple classic profile.",
            ],
        },
        {
            "title": f"{lead} Quick Reheat Bowl",
            "prep_style": "Microwave-friendly bowl",
            "cook_time_minutes": 10,
            "seasoning": [
                "black pepper",
                "garlic powder",
                "parsley",
                "salt",
            ],
            "steps": [
                "Pre-cook proteins and carbs in bulk.",
                "Store fats separately if possible.",
                "Reheat and finish with fresh herbs or citrus.",
            ],
            "meal_prep_tip": "Best for work lunches because all ingredients reheat predictably.",
            "variation_options": [
                "Add lemon after reheating for brightness.",
                "Keep herbs separate and add at serving.",
                "Use a lower-salt version for repeated daily meals.",
            ],
        },
        {
            "title": f"{lead} Savory {('and ' + secondary) if secondary else 'Meal'} Mix",
            "prep_style": "Saute + toss",
            "cook_time_minutes": 20,
            "seasoning": [
                "Italian seasoning",
                "garlic powder",
                "pepper",
                "salt",
            ],
            "steps": [
                "Cook protein first and set aside.",
                "Warm carbs and combine with seasoning blend.",
                "Fold in protein and portion fats as a topping or side.",
            ],
            "meal_prep_tip": "Keep a note of the exact food weights used: " + joined_foods,
            "variation_options": [
                "Italian-style herbs + pepper",
                "Smoky paprika + cumin",
                "Garlic + citrus finish",
            ],
        },
    ]

    return [dict(templates[idx]) for idx in range(min(idea_count, len(templates)))]


def _llm_schema_example() -> dict[str, Any]:
    return {
        "meal_number": 2,
        "ideas": [
            {
                "title": "Lemon Garlic Chicken Rice Bowl",
                "prep_style": "Skillet + bowl",
                "cook_time_minutes": 20,
                "seasoning": ["garlic powder", "black pepper", "paprika", "salt", "lemon juice"],
                "steps": ["...", "...", "..."],
                "meal_prep_tip": "Store sauce separately.",
                "variation_options": ["Option A", "Option B", "Option C"],
            }
        ],
    }


def build_meal_recipe_prompt(meal: dict[str, Any], idea_count: int) -> list[dict[str, str]]:
    slots = _usable_slots(meal)
    slot_lines = "\n".join(
        [f"- {row['slot_key']}: {row['name']} ({row['amount_oz']} oz / {row['amount_g']} g)" for row in slots]
    )
    example_json = json.dumps(_llm_schema_example(), indent=2)

    system = (
        "You are a meal-prep recipe assistant. Generate recipe ideas ONLY using the provided foods. "
        "Do not change quantities. Do not add major ingredients beyond basic seasonings, herbs, acids, and cooking spray/oil. "
        "Return valid JSON only."
    )
    user = (
        f"Create {idea_count} recipe/prep ideas for this generated meal.\n"
        f"Meal number: {meal.get('meal_number')}\n"
        f"Combo ID: {meal.get('combo_id')}\n"
        "Foods and exact amounts:\n"
        f"{slot_lines or '- No usable foods provided'}\n\n"
        "Requirements:\n"
        "- Keep the listed food amounts unchanged.\n"
        "- Focus on prep method and seasoning combinations.\n"
        "- Each idea should have: title, prep_style, cook_time_minutes, seasoning (array), steps (3-5), meal_prep_tip.\n"
        "- Each idea should also include variation_options: array of exactly 3 short alternatives (seasoning or prep twists).\n"
        "- Use concise, practical instructions for gym meal prep.\n"
        f"- Return JSON matching this shape (values can differ): {example_json}\n"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _extract_json_blob(text: str) -> str:
    value = (text or "").strip()
    if not value:
        return ""
    if value.startswith("```"):
        lines = value.splitlines()
        if len(lines) >= 3 and lines[0].startswith("```") and lines[-1].startswith("```"):
            return "\n".join(lines[1:-1]).strip()
    start = value.find("{")
    end = value.rfind("}")
    if start != -1 and end != -1 and end > start:
        return value[start : end + 1]
    return value


def parse_meal_recipe_response(raw_text: str, meal: dict[str, Any], idea_count: int) -> list[dict[str, Any]]:
    ideas: list[dict[str, Any]] = []
    try:
        payload = json.loads(_extract_json_blob(raw_text))
    except Exception:
        return _mock_recipe_ideas_for_meal(meal, idea_count)

    raw_ideas = payload.get("ideas") if isinstance(payload, dict) else None
    if not isinstance(raw_ideas, list):
        return _mock_recipe_ideas_for_meal(meal, idea_count)

    for item in raw_ideas[:idea_count]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip() or f"Meal {meal.get('meal_number')} Idea"
        prep_style = str(item.get("prep_style") or "").strip() or "Simple prep"
        try:
            cook_time_minutes = max(1, int(item.get("cook_time_minutes") or 15))
        except (TypeError, ValueError):
            cook_time_minutes = 15

        seasoning = item.get("seasoning") or []
        if not isinstance(seasoning, list):
            seasoning = [str(seasoning)]
        seasoning = [str(x).strip() for x in seasoning if str(x).strip()][:8]

        steps = item.get("steps") or []
        if not isinstance(steps, list):
            steps = [str(steps)]
        steps = [str(x).strip() for x in steps if str(x).strip()][:5]
        if not steps:
            steps = ["Cook the listed foods with your preferred seasoning blend and portion by weight."]

        meal_prep_tip = str(item.get("meal_prep_tip") or "").strip() or "Portion ingredients by weight after cooking."
        variation_options = item.get("variation_options") or []
        if not isinstance(variation_options, list):
            variation_options = [str(variation_options)]
        variation_options = [str(x).strip() for x in variation_options if str(x).strip()][:3]
        while len(variation_options) < 3:
            variation_options.append(f"Variation option {len(variation_options) + 1}")

        ideas.append(
            {
                "title": title,
                "prep_style": prep_style,
                "cook_time_minutes": cook_time_minutes,
                "seasoning": seasoning,
                "steps": steps,
                "meal_prep_tip": meal_prep_tip,
                "variation_options": variation_options,
            }
        )

    return ideas or _mock_recipe_ideas_for_meal(meal, idea_count)


def _openai_chat_completion(messages: list[dict[str, str]]) -> ProviderResult:
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not configured.")

    model = (os.getenv("OPENAI_RECIPE_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-4.1-mini").strip()
    base_url = (os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
    timeout_seconds = int(os.getenv("OPENAI_TIMEOUT_SECONDS") or "30")

    response = requests.post(
        f"{base_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "response_format": {"type": "json_object"},
        },
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    data = response.json()
    content = (
        (((data.get("choices") or [{}])[0]).get("message") or {}).get("content")
        or ""
    )
    if not content:
        raise ValueError("Empty AI response content.")
    return ProviderResult(provider="openai", model=model, raw_text=content)


def _provider_mode(requested_provider: str | None = None) -> str:
    value = (requested_provider or os.getenv("AI_RECIPE_SUGGESTIONS_PROVIDER") or "mock").strip().lower()
    if value not in {"mock", "openai", "auto"}:
        return "mock"
    return value


def generate_recipe_ideas_for_day(
    *,
    day_detail: dict[str, Any],
    ideas_per_meal: int = DEFAULT_IDEAS_PER_MEAL,
    provider: str | None = None,
    meal_number: int | None = None,
) -> dict[str, Any]:
    ideas_per_meal = normalize_ideas_per_meal(ideas_per_meal)
    provider_mode = _provider_mode(provider)
    requested_meals = list(day_detail.get("meals") or [])
    if meal_number is not None:
        requested_meals = [meal for meal in requested_meals if int(meal.get("meal_number") or 0) == int(meal_number)]

    output_meals = []
    resolved_provider = "mock"
    resolved_model = "mock-v1"

    for meal in requested_meals:
        usable_slots = _usable_slots(meal)
        if not usable_slots:
            output_meals.append(
                {
                    "meal_number": meal.get("meal_number"),
                    "combo_id": meal.get("combo_id"),
                    "ideas": [],
                    "note": "No usable food slots found for this meal.",
                }
            )
            continue

        if provider_mode == "mock":
            ideas = _mock_recipe_ideas_for_meal(meal, ideas_per_meal)
            output_meals.append(
                {
                    "meal_number": meal.get("meal_number"),
                    "combo_id": meal.get("combo_id"),
                    "foods": usable_slots,
                    "ideas": ideas,
                }
            )
            continue

        try:
            provider_result = _openai_chat_completion(build_meal_recipe_prompt(meal, ideas_per_meal))
            resolved_provider = provider_result.provider
            resolved_model = provider_result.model
            ideas = parse_meal_recipe_response(provider_result.raw_text, meal, ideas_per_meal)
            output_meals.append(
                {
                    "meal_number": meal.get("meal_number"),
                    "combo_id": meal.get("combo_id"),
                    "foods": usable_slots,
                    "ideas": ideas,
                }
            )
        except Exception as exc:
            if provider_mode == "openai":
                raise
            # auto mode falls back to mock if the provider is unavailable or fails.
            ideas = _mock_recipe_ideas_for_meal(meal, ideas_per_meal)
            output_meals.append(
                {
                    "meal_number": meal.get("meal_number"),
                    "combo_id": meal.get("combo_id"),
                    "foods": usable_slots,
                    "ideas": ideas,
                    "fallback_reason": str(exc),
                }
            )

    if provider_mode == "openai":
        resolved_provider = "openai"
        if not resolved_model:
            resolved_model = (os.getenv("OPENAI_RECIPE_MODEL") or os.getenv("OPENAI_MODEL") or "unknown").strip()
    elif provider_mode == "auto" and resolved_provider == "mock":
        resolved_model = "mock-fallback-v1"

    return {
        "job_id": day_detail.get("job_id"),
        "day_of_week": day_detail.get("day_of_week"),
        "ideas_per_meal": ideas_per_meal,
        "provider_requested": provider_mode,
        "provider_used": resolved_provider,
        "model": resolved_model,
        "generated_at": _utc_now_iso(),
        "meals": output_meals,
    }
