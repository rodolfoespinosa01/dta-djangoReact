from django.test import SimpleTestCase

from users.client_area.services.ai_recipe_suggestions import (
    build_meal_recipe_prompt,
    generate_recipe_ideas_for_day,
    normalize_ideas_per_meal,
    parse_meal_recipe_response,
)


class AIRecipeSuggestionsTests(SimpleTestCase):
    def _sample_day_detail(self):
        return {
            "job_id": 123,
            "day_of_week": "monday",
            "meals": [
                {
                    "meal_number": 1,
                    "combo_id": 77,
                    "slots": {
                        "protein_1": {"name": "Chicken Breast", "amount_oz": 6, "amount_g": 170.1},
                        "protein_2": {"name": "-", "amount_oz": 0, "amount_g": 0},
                        "carbs_1": {"name": "Brown Rice", "amount_oz": 5, "amount_g": 141.7},
                        "carbs_2": {"name": "-", "amount_oz": 0, "amount_g": 0},
                        "fats_1": {"name": "Avocado", "amount_oz": 1, "amount_g": 28.35},
                        "fats_2": {"name": "-", "amount_oz": 0, "amount_g": 0},
                    },
                }
            ],
        }

    def test_normalize_ideas_per_meal_bounds(self):
        self.assertEqual(normalize_ideas_per_meal(None), 3)
        self.assertEqual(normalize_ideas_per_meal(0), 1)
        self.assertEqual(normalize_ideas_per_meal(99), 5)

    def test_prompt_includes_foods_and_constraints(self):
        meal = self._sample_day_detail()["meals"][0]
        messages = build_meal_recipe_prompt(meal, 3)
        text = "\n".join([m["content"] for m in messages])
        self.assertIn("Chicken Breast", text)
        self.assertIn("Brown Rice", text)
        self.assertIn("Keep the listed food amounts unchanged", text)

    def test_parse_invalid_json_falls_back_to_mock(self):
        meal = self._sample_day_detail()["meals"][0]
        ideas = parse_meal_recipe_response("not-json", meal, 3)
        self.assertEqual(len(ideas), 3)
        self.assertTrue(all("title" in idea for idea in ideas))

    def test_generate_recipe_ideas_mock_mode(self):
        payload = generate_recipe_ideas_for_day(
            day_detail=self._sample_day_detail(),
            ideas_per_meal=2,
            provider="mock",
        )
        self.assertEqual(payload["provider_used"], "mock")
        self.assertEqual(payload["ideas_per_meal"], 2)
        self.assertEqual(len(payload["meals"]), 1)
        self.assertEqual(len(payload["meals"][0]["ideas"]), 2)
