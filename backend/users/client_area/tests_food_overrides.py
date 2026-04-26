from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from core.models import FoodLibraryItem, MealComboTemplate
from users.client_area.models import (
    ClientFoodOverride,
    ClientMealComboSelection,
    ClientMealPlanGeneratedMeal,
    ClientMealPlanGenerationJob,
    ClientMealPlanGenerationStep1Row,
)
from users.client_area.services.meal_plan_generation.pipeline import run_steps_2_to_10_for_day


class ClientFoodOverrideApiTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.User = get_user_model()
        self.user = self.User.objects.create_user(
            username="client@example.com",
            email="client@example.com",
            password="pass12345",
            role="client",
        )
        self.other_user = self.User.objects.create_user(
            username="other@example.com",
            email="other@example.com",
            password="pass12345",
            role="client",
        )
        MealComboTemplate.objects.create(
            combo_id=1,
            protein_slot_1="Ground Beef STANDARD",
            protein_slot_2="-",
            carb_slot_1="White Rice STANDARD",
            carb_slot_2="-",
            fat_slot_1="Avocado STANDARD",
            fat_slot_2="-",
        )

    def test_override_can_be_saved_listed_and_deactivated(self):
        self.api.force_authenticate(user=self.user)
        details = {
            "fdc_id": "123",
            "display_name": "Walmart - Ground Beef 93/7",
            "brand_name": "Walmart",
            "serving_size": Decimal("112"),
            "serving_unit": "g",
            "serving_weight_grams": Decimal("112"),
            "protein": Decimal("5.821"),
            "carbs": Decimal("0"),
            "fats": Decimal("2.025"),
            "calories": Decimal("43.00"),
            "raw_payload": {"fdcId": 123},
        }

        with patch("users.client_area.views.food_overrides.get_food_details", return_value=details):
            response = self.api.post(
                "/api/v1/users/client/app/food-overrides/save/",
                {"canonical_category": "Ground Beef STANDARD", "fdc_id": "123"},
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        saved = response.data["food_override"]
        self.assertEqual(saved["canonical_category"], "Ground Beef STANDARD")
        self.assertEqual(saved["external_provider"], "usda")
        self.assertEqual(saved["external_food_id"], "123")

        listed = self.api.get("/api/v1/users/client/app/food-overrides/")
        self.assertEqual(len(listed.data["food_overrides"]), 1)

        deleted = self.api.delete(f"/api/v1/users/client/app/food-overrides/{saved['id']}/")
        self.assertEqual(deleted.status_code, 200)
        self.assertFalse(ClientFoodOverride.objects.get(id=saved["id"]).active)

    def test_one_user_cannot_see_or_delete_another_users_overrides(self):
        override = ClientFoodOverride.objects.create(
            user=self.other_user,
            canonical_category="Ground Beef STANDARD",
            external_food_id="999",
            display_name="Other User Food",
            protein=1,
        )

        self.api.force_authenticate(user=self.user)

        listed = self.api.get("/api/v1/users/client/app/food-overrides/")
        self.assertEqual(listed.data["food_overrides"], [])

        deleted = self.api.delete(f"/api/v1/users/client/app/food-overrides/{override.id}/")
        self.assertEqual(deleted.status_code, 404)
        override.refresh_from_db()
        self.assertTrue(override.active)

    def test_usda_search_response_does_not_expose_api_key(self):
        self.api.force_authenticate(user=self.user)
        with patch("users.client_area.views.food_overrides.search_foods") as search:
            search.return_value = {
                "foods": [
                    {
                        "fdc_id": "123",
                        "display_name": "Food",
                        "brand_name": "Brand",
                        "data_type": "Branded",
                        "serving_size": Decimal("100"),
                        "serving_unit": "g",
                        "serving_weight_grams": Decimal("100"),
                        "protein": Decimal("1"),
                        "carbs": Decimal("2"),
                        "fats": Decimal("3"),
                        "calories": Decimal("4"),
                    }
                ],
                "page": 1,
                "page_size": 10,
                "total_hits": 1,
                "total_pages": 1,
            }

            response = self.api.post(
                "/api/v1/users/client/app/food-overrides/usda/search/",
                {"query": "food", "page_size": 10},
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("api_key", str(response.data).lower())

    def test_usda_specific_foods_do_not_appear_in_template_dropdowns(self):
        ClientFoodOverride.objects.create(
            user=self.user,
            canonical_category="Ground Beef STANDARD",
            external_food_id="123",
            display_name="Walmart Ground Beef 93/7",
            protein=1,
        )

        response = self.api.get("/api/v1/users/client/public/meal-combo-options/")

        self.assertEqual(response.status_code, 200)
        protein_options = response.data["slot_options"]["protein_1"]
        self.assertIn("Ground Beef STANDARD", protein_options)
        self.assertNotIn("Walmart Ground Beef 93/7", protein_options)


class ClientFoodOverrideGenerationTests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.user = self.User.objects.create_user(
            username="generation@example.com",
            email="generation@example.com",
            password="pass12345",
            role="client",
        )
        FoodLibraryItem.objects.create(
            source_food_id=1,
            category="Chicken Breast STANDARD",
            name="Chicken Breast STANDARD",
            canonical_category="Chicken Breast STANDARD",
            protein=Decimal("5.00000"),
            carbs=0,
            fats=0,
            measurement_unit="oz",
        )
        self.combo = MealComboTemplate.objects.create(
            combo_id=10,
            protein_slot_1="Chicken Breast STANDARD",
            protein_slot_2="-",
            carb_slot_1="-",
            carb_slot_2="-",
            fat_slot_1="-",
            fat_slot_2="-",
            protein_split_1=Decimal("1.00"),
            protein_split_2=Decimal("0.00"),
            carb_split_1=Decimal("0.00"),
            carb_split_2=Decimal("0.00"),
            fat_split_1=Decimal("0.00"),
            fat_split_2=Decimal("0.00"),
        )
        ClientMealComboSelection.objects.create(
            user=self.user,
            day_of_week="sunday",
            meal_number=1,
            combo_template=self.combo,
        )

    def _run_generation(self):
        job = ClientMealPlanGenerationJob.objects.create(
            user=self.user,
            day_of_week="sunday",
            status="running",
            input_snapshot_json={
                "day_selected_slot_foods": {
                    "1": {
                        "protein_1": "Chicken Breast STANDARD",
                        "protein_2": "-",
                        "carbs_1": "-",
                        "carbs_2": "-",
                        "fats_1": "-",
                        "fats_2": "-",
                    }
                }
            },
        )
        ClientMealPlanGenerationStep1Row.objects.create(
            job=job,
            meal_number=1,
            error_code=7,
            pro_negative=Decimal("40.000000"),
            carbs_negative=Decimal("0.000000"),
            fats_negative=Decimal("0.000000"),
        )
        run_steps_2_to_10_for_day(
            job=job,
            day_payload={
                "day": "sunday",
                "training_before_meal": None,
                "meal_macro_splits": [
                    {"meal_number": 1, "grams": {"protein_g": 40, "carbs_g": 0, "fats_g": 0}}
                ],
            },
        )
        return ClientMealPlanGeneratedMeal.objects.get(job=job, meal_number=1)

    def test_generation_uses_default_food_macros_when_no_override_exists(self):
        row = self._run_generation()

        self.assertEqual(row.combo_template_id, 10)
        self.assertEqual(row.error_code, 7)
        self.assertEqual(row.protein1_total, Decimal("8.000000"))

    def test_generation_uses_override_macros_for_final_amounts_without_changing_combo_or_error(self):
        ClientFoodOverride.objects.create(
            user=self.user,
            canonical_category="Chicken Breast STANDARD",
            external_food_id="123",
            display_name="USDA Chicken",
            protein=Decimal("10.00000"),
            carbs=0,
            fats=0,
            calories=0,
        )

        row = self._run_generation()

        self.assertEqual(row.combo_template_id, 10)
        self.assertEqual(row.error_code, 7)
        self.assertEqual(row.protein1_total, Decimal("4.000000"))
