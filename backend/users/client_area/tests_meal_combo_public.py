from django.test import TestCase
from rest_framework.test import APIClient

from core.models import FoodLibraryItem, MealComboTemplate
from users.client_area.views.meal_combo_public import _combo_to_payload


class MealComboPublicOptionsTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        FoodLibraryItem.objects.bulk_create(
            [
                FoodLibraryItem(
                    source_food_id=1,
                    category="Ground Beef STANDARD",
                    name="Ground Beef 95/5",
                    measurement_unit="oz",
                    protein=24,
                    carbs=0,
                    fats=5,
                ),
                FoodLibraryItem(
                    source_food_id=2,
                    category="Ground Beef STANDARD",
                    name="Ground Beef 90/10",
                    measurement_unit="oz",
                    protein=22,
                    carbs=0,
                    fats=10,
                ),
            ]
        )
        MealComboTemplate.objects.create(
            combo_id=501,
            protein_slot_1="Ground Beef STANDARD",
            protein_slot_2="-",
            carb_slot_1="White Rice",
            carb_slot_2="-",
            fat_slot_1="Avocado",
            fat_slot_2="Oil STANDARD",
        )

    def test_slot_options_use_combo_template_values_not_food_library_names(self):
        response = self.api.get("/api/v1/users/client/public/meal-combo-options/")

        self.assertEqual(response.status_code, 200)
        protein_options = response.data["slot_options"]["protein_1"]
        self.assertIn("Ground Beef STANDARD", protein_options)
        self.assertNotIn("Ground Beef 95/5", protein_options)
        self.assertNotIn("Ground Beef 90/10", protein_options)

    def test_lookup_normalizes_legacy_food_names_before_combo_match(self):
        response = self.api.post(
            "/api/v1/users/client/public/meal-combo-lookup/",
            {
                "protein_1": "Ground Beef 95/5",
                "protein_2": "-",
                "carbs_1": "White Rice",
                "carbs_2": "-",
                "fats_1": "Avocado",
                "fats_2": "Oil STANDARD",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["combo_match"]["found"])
        self.assertEqual(response.data["combo_match"]["combo_id"], 501)
        self.assertEqual(response.data["combo_match"]["slots"]["protein_1"], "Ground Beef STANDARD")

    def test_combo_payload_uses_template_slot_values_for_starter_rows(self):
        combo = MealComboTemplate.objects.get(combo_id=501)

        payload = _combo_to_payload(combo)

        self.assertEqual(payload["protein_1"], "Ground Beef STANDARD")
        self.assertNotEqual(payload["protein_1"], "Ground Beef 95/5")
