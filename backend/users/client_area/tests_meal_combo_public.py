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
                    name="Ground Beef STANDARD",
                    display_name="Ground Beef 95/5",
                    measurement_unit="oz",
                    protein=24,
                    carbs=0,
                    fats=5,
                ),
                FoodLibraryItem(
                    source_food_id=2,
                    category="Ground Beef STANDARD",
                    name="Ground Beef STANDARD",
                    display_name="Ground Beef 90/10",
                    measurement_unit="oz",
                    protein=22,
                    carbs=0,
                    fats=10,
                ),
                FoodLibraryItem(
                    source_food_id=3,
                    category="Ground Beef STANDARD",
                    name="User Ground Beef",
                    display_name="User Ground Beef",
                    measurement_unit="oz",
                    protein=99,
                    carbs=99,
                    fats=99,
                    source_type=FoodLibraryItem.SourceType.USER_SUBMITTED,
                    approval_status=FoodLibraryItem.ApprovalStatus.PENDING,
                    is_standard=False,
                ),
            ]
        )
        MealComboTemplate.objects.create(
            combo_id=501,
            protein_slot_1="Ground Beef STANDARD",
            protein_slot_2="-",
            carb_slot_1="White Rice STANDARD",
            carb_slot_2="-",
            fat_slot_1="Avocado STANDARD",
            fat_slot_2="Oil STANDARD",
        )

    def test_slot_options_use_combo_template_values_not_food_library_names(self):
        response = self.api.get("/api/v1/users/client/public/meal-combo-options/")

        self.assertEqual(response.status_code, 200)
        protein_options = response.data["slot_options"]["protein_1"]
        self.assertIn("Ground Beef STANDARD", protein_options)
        self.assertNotIn("Ground Beef 95/5", protein_options)
        self.assertNotIn("Ground Beef 90/10", protein_options)
        self.assertNotIn("User Ground Beef", protein_options)

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
        self.assertEqual(response.data["combo_match"]["slots"]["carbs_1"], "White Rice STANDARD")
        self.assertEqual(response.data["combo_match"]["slots"]["fats_1"], "Avocado STANDARD")

    def test_combo_payload_uses_template_slot_values_for_starter_rows(self):
        combo = MealComboTemplate.objects.get(combo_id=501)

        payload = _combo_to_payload(combo)

        self.assertEqual(payload["protein_1"], "Ground Beef STANDARD")
        self.assertNotEqual(payload["protein_1"], "Ground Beef 95/5")


class MealComboStarterTemplateShapePolicyTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        MealComboTemplate.objects.bulk_create(
            [
                MealComboTemplate(
                    combo_id=100,
                    protein_slot_1="Chicken Breast STANDARD",
                    protein_slot_2="Eggs STANDARD",
                    carb_slot_1="White Rice STANDARD",
                    carb_slot_2="-",
                    fat_slot_1="Avocado STANDARD",
                    fat_slot_2="Oil STANDARD",
                ),
                MealComboTemplate(
                    combo_id=101,
                    protein_slot_1="Chicken Breast STANDARD",
                    protein_slot_2="-",
                    carb_slot_1="White Rice STANDARD",
                    carb_slot_2="-",
                    fat_slot_1="Avocado STANDARD",
                    fat_slot_2="Oil STANDARD",
                ),
                MealComboTemplate(
                    combo_id=102,
                    protein_slot_1="Chicken Breast STANDARD",
                    protein_slot_2="-",
                    carb_slot_1="Brown Rice STANDARD",
                    carb_slot_2="-",
                    fat_slot_1="Avocado STANDARD",
                    fat_slot_2="Oil STANDARD",
                ),
                MealComboTemplate(
                    combo_id=103,
                    protein_slot_1="Chicken Breast STANDARD",
                    protein_slot_2="Ground Beef STANDARD",
                    carb_slot_1="Brown Rice STANDARD",
                    carb_slot_2="-",
                    fat_slot_1="Avocado STANDARD",
                    fat_slot_2="Oil STANDARD",
                ),
                MealComboTemplate(
                    combo_id=104,
                    protein_slot_1="Chicken Breast STANDARD",
                    protein_slot_2="-",
                    carb_slot_1="White Rice STANDARD",
                    carb_slot_2="Banana STANDARD",
                    fat_slot_1="Avocado STANDARD",
                    fat_slot_2="Oil STANDARD",
                ),
                MealComboTemplate(
                    combo_id=105,
                    protein_slot_1="Chicken Breast STANDARD",
                    protein_slot_2="-",
                    carb_slot_1="Quinoa STANDARD",
                    carb_slot_2="Banana STANDARD",
                    fat_slot_1="Avocado STANDARD",
                    fat_slot_2="Oil STANDARD",
                ),
                MealComboTemplate(
                    combo_id=106,
                    protein_slot_1="Chicken Breast STANDARD",
                    protein_slot_2="Eggs STANDARD",
                    carb_slot_1="Quinoa STANDARD",
                    carb_slot_2="Banana STANDARD",
                    fat_slot_1="Avocado STANDARD",
                    fat_slot_2="Oil STANDARD",
                ),
                MealComboTemplate(
                    combo_id=107,
                    protein_slot_1="Chicken Breast STANDARD",
                    protein_slot_2="-",
                    carb_slot_1="Brown Rice STANDARD",
                    carb_slot_2="Beans STANDARD",
                    fat_slot_1="Avocado STANDARD",
                    fat_slot_2="Oil STANDARD",
                ),
            ]
        )

    def _day_payload(self, *, protein, carbs, training_before_meal=None):
        return {
            "day": "saturday",
            "is_workout_day": bool(training_before_meal),
            "training_before_meal": training_before_meal,
            "meals_per_day": 3,
            "meal_macro_splits": [
                {
                    "meal_number": meal_number,
                    "grams": {"protein_g": protein, "carbs_g": carbs, "fats_g": 12},
                }
                for meal_number in (1, 2, 3)
            ],
        }

    def _starter(self, payload):
        return self.api.post(
            "/api/v1/users/client/public/meal-combo-starter-templates/?count=1",
            {"day_payload": payload},
            format="json",
        )

    def test_low_protein_low_carb_no_training_starter_prefers_one_protein_one_carb(self):
        response = self._starter(self._day_payload(protein=38.67, carbs=40.04))

        self.assertEqual(response.status_code, 200)
        meals = response.data["starter_templates"][0]["default_day_meals"]
        self.assertEqual(len(meals), 3)
        for meal in meals:
            self.assertEqual(meal["protein_2"], "-")
            self.assertEqual(meal["carbs_2"], "-")

    def test_low_protein_starter_does_not_choose_two_protein_when_one_protein_exists(self):
        response = self._starter(self._day_payload(protein=40, carbs=65))

        self.assertEqual(response.status_code, 200)
        meals = response.data["starter_templates"][0]["default_day_meals"]
        self.assertTrue(all(meal["protein_2"] == "-" for meal in meals))

    def test_low_carb_no_training_starter_does_not_choose_two_carb_when_one_carb_exists(self):
        response = self._starter(self._day_payload(protein=55, carbs=35))

        self.assertEqual(response.status_code, 200)
        meals = response.data["starter_templates"][0]["default_day_meals"]
        self.assertTrue(all(meal["carbs_2"] == "-" for meal in meals))

    def test_high_protein_starter_can_choose_two_protein_template(self):
        response = self._starter(self._day_payload(protein=55, carbs=40))

        self.assertEqual(response.status_code, 200)
        meal_1 = response.data["starter_templates"][0]["default_day_meals"][0]
        self.assertEqual(meal_1["protein_2"], "Eggs STANDARD")

    def test_training_adjacent_moderate_carb_starter_can_choose_two_carb_template(self):
        response = self._starter(self._day_payload(protein=40, carbs=50, training_before_meal="before_meal_2"))

        self.assertEqual(response.status_code, 200)
        meals = response.data["starter_templates"][0]["default_day_meals"]
        self.assertEqual(meals[0]["carbs_2"], "Banana STANDARD")
        self.assertEqual(meals[1]["carbs_2"], "Banana STANDARD")

    def test_high_carb_starter_can_choose_two_carb_template(self):
        response = self._starter(self._day_payload(protein=40, carbs=65))

        self.assertEqual(response.status_code, 200)
        meals = response.data["starter_templates"][0]["default_day_meals"]
        self.assertIn("Banana STANDARD", {meal["carbs_2"] for meal in meals})
