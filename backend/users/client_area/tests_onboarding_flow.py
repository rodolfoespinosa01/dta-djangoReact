from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from core.models import MealComboTemplate
from users.client_area.models import ClientProfile, ClientQuestionnaireProgress


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
