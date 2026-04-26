from django.contrib.auth import get_user_model
from django.test import TestCase
from unittest.mock import patch
from rest_framework.test import APIClient

from core.models import FoodLibraryItem, MealComboTemplate
from users.client_area.models import ClientMealComboSelection, ClientProfile, ClientQuestionnaireProgress


QUESTIONNAIRE_ANSWERS = {
    "gender": "male",
    "height": {"unit": "cm", "value": 180},
    "weight": {"unit": "lbs", "value": 180},
    "date_of_birth": "1990-01-01",
    "goal": "maintain",
    "lifestyle": "moderate",
    "meal_plan_type": "standard",
    "workout_days": ["monday"],
    "meal_schedule": {
        "mode": "same",
        "default_meals": 3,
        "days": {
            "sunday": 3,
            "monday": 3,
            "tuesday": 3,
            "wednesday": 3,
            "thursday": 3,
            "friday": 3,
            "saturday": 3,
        },
    },
    "training_schedule": {"monday": "before_meal_1"},
}


def weekly_combo_payload(combo_id=1):
    meal = {
        "protein_1": "-",
        "protein_2": "-",
        "carbs_1": "-",
        "carbs_2": "-",
        "fats_1": "-",
        "fats_2": "-",
        "combo_id": combo_id,
    }
    return {
        "weekly_days": {
            day: [dict(meal), dict(meal), dict(meal)]
            for day in ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
        }
    }


class ClientOnboardingFlowTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.User = get_user_model()

    def create_client_user(self, email, includes_food_plan):
        user = self.User.objects.create_user(username=email, email=email, password="pass12345", role="client")
        ClientProfile.objects.create(
            user=user,
            offer_code="food_plan_monthly" if includes_food_plan else "macro_calculator_free",
            billing_cycle="monthly" if includes_food_plan else "free",
            includes_food_plan=includes_food_plan,
            includes_coaching=False,
            sale_channel="dta_direct",
        )
        progress = ClientQuestionnaireProgress.objects.create(
            user=user,
            status="completed",
            current_step="training_schedule",
            answers_json=dict(QUESTIONNAIRE_ANSWERS),
        )
        return user, progress

    def test_standard_client_requires_food_preferences_before_dashboard_complete(self):
        user, _ = self.create_client_user("standard@example.com", includes_food_plan=True)
        self.api.force_authenticate(user=user)

        response = self.api.get("/api/v1/users/client/app/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["onboarding"]["next_step"], "food_preferences")
        self.assertTrue(response.data["onboarding"]["requires_food_preferences"])
        self.assertFalse(response.data["onboarding"]["food_preferences_completed"])

    def test_macro_client_is_not_forced_into_food_preferences(self):
        user, _ = self.create_client_user("macro@example.com", includes_food_plan=False)
        self.api.force_authenticate(user=user)

        response = self.api.get("/api/v1/users/client/app/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["onboarding"]["next_step"], "dashboard")
        self.assertFalse(response.data["onboarding"]["requires_food_preferences"])

    def test_food_preferences_submit_marks_completion(self):
        user, progress = self.create_client_user("foods@example.com", includes_food_plan=True)
        MealComboTemplate.objects.create(combo_id=1)
        self.api.force_authenticate(user=user)

        response = self.api.put(
            "/api/v1/users/client/app/food-preferences/",
            {"builder_value": weekly_combo_payload(1)},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        progress.refresh_from_db()
        self.assertTrue(progress.answers_json.get("food_preferences"))

        dashboard = self.api.get("/api/v1/users/client/app/dashboard/")
        self.assertEqual(dashboard.data["onboarding"]["next_step"], "dashboard")
        self.assertTrue(dashboard.data["onboarding"]["food_preferences_completed"])

    def test_food_preferences_store_template_slot_values_not_food_variations(self):
        user, progress = self.create_client_user("slot-values@example.com", includes_food_plan=True)
        FoodLibraryItem.objects.create(
            source_food_id=900,
            category="Ground Beef STANDARD",
            name="Ground Beef STANDARD",
            display_name="Ground Beef 95/5",
            measurement_unit="oz",
            protein=24,
            carbs=0,
            fats=5,
        )
        MealComboTemplate.objects.create(
            combo_id=77,
            protein_slot_1="Ground Beef STANDARD",
            protein_slot_2="-",
            carb_slot_1="White Rice STANDARD",
            carb_slot_2="-",
            fat_slot_1="Avocado STANDARD",
            fat_slot_2="Oil STANDARD",
        )
        meal = {
            "protein_1": "Ground Beef 95/5",
            "protein_2": "-",
            "carbs_1": "White Rice",
            "carbs_2": "-",
            "fats_1": "Avocado",
            "fats_2": "Oil STANDARD",
        }
        payload = {
            "weekly_days": {
                day: [dict(meal), dict(meal), dict(meal)]
                for day in ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
            }
        }
        self.api.force_authenticate(user=user)

        response = self.api.put(
            "/api/v1/users/client/app/food-preferences/",
            {"builder_value": payload},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        progress.refresh_from_db()
        saved_meal = progress.answers_json["food_preferences"]["weekly_days"]["sunday"][0]
        self.assertEqual(saved_meal["protein_1"], "Ground Beef STANDARD")
        self.assertEqual(saved_meal["carbs_1"], "White Rice STANDARD")
        self.assertEqual(saved_meal["fats_1"], "Avocado STANDARD")
        self.assertEqual(saved_meal["combo_id"], 77)

    def test_food_preferences_save_reselects_low_macro_combos_before_persisting(self):
        user, progress = self.create_client_user("shape-save@example.com", includes_food_plan=True)
        two_slot = MealComboTemplate.objects.create(
            combo_id=8084,
            protein_slot_1="Chicken Breast STANDARD",
            protein_slot_2="Eggs STANDARD",
            carb_slot_1="White Rice STANDARD",
            carb_slot_2="Banana STANDARD",
            fat_slot_1="Avocado STANDARD",
            fat_slot_2="Oil STANDARD",
        )
        one_slot = MealComboTemplate.objects.create(
            combo_id=8121,
            protein_slot_1="Chicken Breast STANDARD",
            protein_slot_2="-",
            carb_slot_1="White Rice STANDARD",
            carb_slot_2="-",
            fat_slot_1="Avocado STANDARD",
            fat_slot_2="Oil STANDARD",
        )
        bad_meal = {
            "protein_1": two_slot.protein_slot_1,
            "protein_2": two_slot.protein_slot_2,
            "carbs_1": two_slot.carb_slot_1,
            "carbs_2": two_slot.carb_slot_2,
            "fats_1": two_slot.fat_slot_1,
            "fats_2": two_slot.fat_slot_2,
            "combo_id": two_slot.combo_id,
        }
        payload = {
            "weekly_days": {
                day: [dict(bad_meal), dict(bad_meal), dict(bad_meal)]
                for day in ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
            }
        }
        low_macro_results = {
            "weekly_days": [
                {
                    "day": day,
                    "training_before_meal": None,
                    "meal_macro_splits": [
                        {"meal_number": idx, "grams": {"protein_g": 38.67, "carbs_g": 40.04, "fats_g": 11.86}}
                        for idx in (1, 2, 3)
                    ],
                }
                for day in ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
            ]
        }
        self.api.force_authenticate(user=user)

        with patch("users.client_area.views.auth_flow.build_questionnaire_results", return_value=low_macro_results):
            response = self.api.put(
                "/api/v1/users/client/app/food-preferences/",
                {"builder_value": payload},
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        progress.refresh_from_db()
        saved_meal = progress.answers_json["food_preferences"]["weekly_days"]["saturday"][0]
        self.assertEqual(saved_meal["combo_id"], one_slot.combo_id)
        self.assertEqual(saved_meal["protein_2"], "-")
        self.assertEqual(saved_meal["carbs_2"], "-")
        self.assertEqual(
            ClientMealComboSelection.objects.get(user=user, day_of_week="saturday", meal_number=1).combo_template_id,
            one_slot.combo_id,
        )
