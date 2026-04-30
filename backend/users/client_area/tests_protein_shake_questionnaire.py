from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from core.models import MealComboTemplate
from users.client_area.models import ClientMealComboSelection, ClientProfile, ClientQuestionnaireProgress
from users.client_area.views.auth_flow import _normalize_questionnaire_answer


WEEK_DAYS = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]


def meal_schedule(default=5, overrides=None):
    days = {day: default for day in WEEK_DAYS}
    days.update(overrides or {})
    return {"mode": "same", "default_meals": default, "days": days}


class ProteinShakeQuestionnaireNormalizationTests(SimpleTestCase):
    def test_disabled_protein_shake_normalizes_correctly(self):
        normalized, error = _normalize_questionnaire_answer("protein_shake", {"enabled": False}, {})

        self.assertIsNone(error)
        self.assertEqual(normalized, {"enabled": False, "counts_as_meal": True})

    def test_same_every_day_post_workout_derives_from_training_meal(self):
        normalized, error = _normalize_questionnaire_answer(
            "protein_shake",
            {"enabled": True, "schedule_mode": "same", "default_timing": "post_workout", "default_selected_meal": 5},
            {"meal_schedule": meal_schedule(5), "training_schedule": {"monday": "before_meal_3"}},
        )

        self.assertIsNone(error)
        self.assertTrue(normalized["counts_as_meal"])
        self.assertEqual(normalized["schedule_mode"], "same")
        self.assertEqual(normalized["days"]["monday"]["selected_meal"], 4)
        self.assertEqual(normalized["selected_meals_by_day"]["monday"], 4)
        self.assertEqual(normalized["default_selected_meal"], 5)
        self.assertFalse(normalized["days"]["sunday"]["enabled"])
        self.assertNotIn("sunday", normalized["selected_meals_by_day"])

    def test_same_every_day_pre_workout_derives_meal_before_training(self):
        normalized, error = _normalize_questionnaire_answer(
            "protein_shake",
            {"enabled": True, "schedule_mode": "same", "default_timing": "pre_workout", "default_selected_meal": 5},
            {"meal_schedule": meal_schedule(5), "training_schedule": {"monday": "before_meal_3"}},
        )

        self.assertIsNone(error)
        self.assertEqual(normalized["days"]["monday"]["selected_meal"], 2)

    def test_same_every_day_other_uses_manual_selected_meal_not_pre_or_post(self):
        normalized, error = _normalize_questionnaire_answer(
            "protein_shake",
            {"enabled": True, "schedule_mode": "same", "default_timing": "other", "default_selected_meal": 2},
            {"meal_schedule": meal_schedule(4), "training_schedule": {"monday": "before_meal_2"}},
        )

        self.assertIsNone(error)
        self.assertEqual(normalized["days"]["monday"], {"enabled": True, "timing": "other", "selected_meal": 2})
        self.assertEqual(normalized["selected_meals_by_day"]["monday"], 2)

    def test_other_invalid_pre_or_post_meal_falls_back_to_first_valid_other_option(self):
        normalized, error = _normalize_questionnaire_answer(
            "protein_shake",
            {"enabled": True, "schedule_mode": "same", "default_timing": "other", "default_selected_meal": 1},
            {"meal_schedule": meal_schedule(4), "training_schedule": {"monday": "before_meal_2"}},
        )

        self.assertIsNone(error)
        self.assertEqual(normalized["days"]["monday"], {"enabled": True, "timing": "other", "selected_meal": 2})

    def test_custom_by_day_other_uses_each_valid_manual_selected_meal(self):
        normalized, error = _normalize_questionnaire_answer(
            "protein_shake",
            {
                "enabled": True,
                "schedule_mode": "custom",
                "days": {
                    "monday": {"enabled": True, "timing": "other", "selected_meal": 5},
                    "tuesday": {"enabled": True, "timing": "other", "selected_meal": 4},
                },
            },
            {
                "meal_schedule": meal_schedule(5, {"tuesday": 4}),
                "training_schedule": {"monday": "before_meal_3", "tuesday": "before_meal_2"},
            },
        )

        self.assertIsNone(error)
        self.assertEqual(normalized["days"]["monday"]["selected_meal"], 5)
        self.assertEqual(normalized["days"]["tuesday"]["selected_meal"], 4)

    def test_other_options_for_training_before_meal_1_fallback_from_pre_or_post(self):
        normalized, error = _normalize_questionnaire_answer(
            "protein_shake",
            {"enabled": True, "schedule_mode": "same", "default_timing": "other", "default_selected_meal": 1},
            {"meal_schedule": meal_schedule(4), "training_schedule": {"monday": "before_meal_1"}},
        )

        self.assertIsNone(error)
        self.assertEqual(normalized["days"]["monday"], {"enabled": True, "timing": "other", "selected_meal": 3})

    def test_other_options_for_training_before_last_meal_fallback_from_pre_or_post(self):
        normalized, error = _normalize_questionnaire_answer(
            "protein_shake",
            {"enabled": True, "schedule_mode": "same", "default_timing": "other", "default_selected_meal": 4},
            {"meal_schedule": meal_schedule(4), "training_schedule": {"monday": "before_meal_4"}},
        )

        self.assertIsNone(error)
        self.assertEqual(normalized["days"]["monday"], {"enabled": True, "timing": "other", "selected_meal": 1})

    def test_other_no_training_allows_all_manual_meals(self):
        normalized, error = _normalize_questionnaire_answer(
            "protein_shake",
            {"enabled": True, "schedule_mode": "same", "default_timing": "other", "default_selected_meal": 4},
            {"meal_schedule": meal_schedule(4), "training_schedule": {}},
        )

        self.assertIsNone(error)
        self.assertTrue(all(day["selected_meal"] == 4 for day in normalized["days"].values()))

    def test_switching_from_post_workout_to_other_stops_forcing_training_meal(self):
        normalized, error = _normalize_questionnaire_answer(
            "protein_shake",
            {
                "enabled": True,
                "schedule_mode": "same",
                "default_timing": "other",
                "default_selected_meal": 5,
                "selected_meal": 3,
                "placement_mode": "post_workout",
            },
            {"meal_schedule": meal_schedule(5), "training_schedule": {"monday": "before_meal_3"}},
        )

        self.assertIsNone(error)
        self.assertEqual(normalized["days"]["monday"], {"enabled": True, "timing": "other", "selected_meal": 5})

    def test_pre_workout_before_meal_1_clamps_to_meal_1(self):
        normalized, error = _normalize_questionnaire_answer(
            "protein_shake",
            {"enabled": True, "schedule_mode": "same", "default_timing": "pre_workout"},
            {"meal_schedule": meal_schedule(5), "training_schedule": {"monday": "before_meal_1"}},
        )

        self.assertIsNone(error)
        self.assertEqual(normalized["days"]["monday"]["selected_meal"], 1)

    def test_four_meals_training_before_meal_2_pre_and_post_slots(self):
        pre, pre_error = _normalize_questionnaire_answer(
            "protein_shake",
            {"enabled": True, "schedule_mode": "same", "default_timing": "pre_workout"},
            {"meal_schedule": meal_schedule(4), "training_schedule": {"monday": "before_meal_2"}},
        )
        post, post_error = _normalize_questionnaire_answer(
            "protein_shake",
            {"enabled": True, "schedule_mode": "same", "default_timing": "post_workout"},
            {"meal_schedule": meal_schedule(4), "training_schedule": {"monday": "before_meal_2"}},
        )

        self.assertIsNone(pre_error)
        self.assertIsNone(post_error)
        self.assertEqual(pre["days"]["monday"]["selected_meal"], 1)
        self.assertEqual(post["days"]["monday"]["selected_meal"], 3)

    def test_four_meals_training_before_meal_1_pre_and_post_slots(self):
        pre, pre_error = _normalize_questionnaire_answer(
            "protein_shake",
            {"enabled": True, "schedule_mode": "same", "default_timing": "pre_workout"},
            {"meal_schedule": meal_schedule(4), "training_schedule": {"monday": "before_meal_1"}},
        )
        post, post_error = _normalize_questionnaire_answer(
            "protein_shake",
            {"enabled": True, "schedule_mode": "same", "default_timing": "post_workout"},
            {"meal_schedule": meal_schedule(4), "training_schedule": {"monday": "before_meal_1"}},
        )

        self.assertIsNone(pre_error)
        self.assertIsNone(post_error)
        self.assertEqual(pre["days"]["monday"]["selected_meal"], 1)
        self.assertEqual(post["days"]["monday"]["selected_meal"], 2)

    def test_four_meals_training_before_meal_4_pre_and_post_slots(self):
        pre, pre_error = _normalize_questionnaire_answer(
            "protein_shake",
            {"enabled": True, "schedule_mode": "same", "default_timing": "pre_workout"},
            {"meal_schedule": meal_schedule(4), "training_schedule": {"monday": "before_meal_4"}},
        )
        post, post_error = _normalize_questionnaire_answer(
            "protein_shake",
            {"enabled": True, "schedule_mode": "same", "default_timing": "post_workout"},
            {"meal_schedule": meal_schedule(4), "training_schedule": {"monday": "before_meal_4"}},
        )

        self.assertIsNone(pre_error)
        self.assertIsNone(post_error)
        self.assertEqual(pre["days"]["monday"]["selected_meal"], 3)
        self.assertEqual(post["days"]["monday"]["selected_meal"], 4)

    def test_custom_by_day_supports_different_timing_and_manual_placement(self):
        normalized, error = _normalize_questionnaire_answer(
            "protein_shake",
            {
                "enabled": True,
                "schedule_mode": "custom",
                "days": {
                    "monday": {"enabled": True, "timing": "post_workout"},
                    "tuesday": {"enabled": True, "timing": "pre_workout"},
                    "wednesday": {"enabled": True, "timing": "other", "selected_meal": 4},
                },
            },
            {
                "meal_schedule": meal_schedule(5, {"tuesday": 4, "wednesday": 4}),
                "training_schedule": {"monday": "before_meal_3", "tuesday": "before_meal_2"},
            },
        )

        self.assertIsNone(error)
        self.assertEqual(normalized["schedule_mode"], "custom")
        self.assertEqual(normalized["days"]["monday"]["selected_meal"], 4)
        self.assertEqual(normalized["days"]["tuesday"]["selected_meal"], 1)
        self.assertEqual(normalized["days"]["wednesday"]["selected_meal"], 4)

    def test_no_training_day_with_pre_or_post_is_disabled_by_default(self):
        normalized, error = _normalize_questionnaire_answer(
            "protein_shake",
            {
                "enabled": True,
                "schedule_mode": "custom",
                "days": {"sunday": {"timing": "post_workout", "selected_meal": 4}},
            },
            {"meal_schedule": meal_schedule(5), "training_schedule": {}},
        )

        self.assertIsNone(error)
        self.assertEqual(normalized["days"]["sunday"], {"enabled": False, "timing": "other", "selected_meal": 1})
        self.assertNotIn("sunday", normalized["selected_meals_by_day"])

    def test_no_training_day_can_be_explicitly_enabled_as_manual_meal_1(self):
        normalized, error = _normalize_questionnaire_answer(
            "protein_shake",
            {
                "enabled": True,
                "schedule_mode": "custom",
                "days": {"sunday": {"enabled": True, "timing": "post_workout", "selected_meal": 4}},
            },
            {"meal_schedule": meal_schedule(5), "training_schedule": {}},
        )

        self.assertIsNone(error)
        self.assertEqual(normalized["days"]["sunday"], {"enabled": True, "timing": "other", "selected_meal": 1})
        self.assertEqual(normalized["selected_meals_by_day"]["sunday"], 1)

    def test_meal_count_changes_clamp_selected_meal(self):
        normalized, error = _normalize_questionnaire_answer(
            "protein_shake",
            {"enabled": True, "schedule_mode": "same", "default_timing": "other", "default_selected_meal": 6},
            {"meal_schedule": meal_schedule(4)},
        )

        self.assertIsNone(error)
        self.assertTrue(all(row["selected_meal"] == 4 for row in normalized["days"].values()))

    def test_old_selected_meal_shape_does_not_crash(self):
        normalized, error = _normalize_questionnaire_answer(
            "protein_shake",
            {
                "enabled": True,
                "counts_as_meal": True,
                "placement_mode": "other",
                "selected_meal": 3,
                "selected_meals_by_day": {"monday": 4},
            },
            {"meal_schedule": meal_schedule(5)},
        )

        self.assertIsNone(error)
        self.assertEqual(normalized["schedule_mode"], "custom")
        self.assertEqual(normalized["selected_meals_by_day"]["monday"], 4)

    def test_old_extra_shake_shape_does_not_crash(self):
        normalized, error = _normalize_questionnaire_answer(
            "protein_shake",
            {
                "enabled": True,
                "mode": "extra_shake",
                "counts_as_meal": False,
                "timing_mode": "post_workout",
            },
            {"meal_schedule": meal_schedule(5), "training_schedule": {"monday": "before_meal_3"}},
        )

        self.assertIsNone(error)
        self.assertTrue(normalized["counts_as_meal"])
        self.assertEqual(normalized["days"]["monday"]["selected_meal"], 4)


def normal_meal_payload(combo_id=1):
    return {
        "protein_1": "-",
        "protein_2": "-",
        "carbs_1": "-",
        "carbs_2": "-",
        "fats_1": "-",
        "fats_2": "-",
        "combo_id": combo_id,
    }


def invalid_meal_payload():
    return {
        "protein_1": "Unknown Protein STANDARD",
        "protein_2": "-",
        "carbs_1": "Unknown Carb STANDARD",
        "carbs_2": "-",
        "fats_1": "Unknown Fat STANDARD",
        "fats_2": "-",
    }


def weekly_builder(meal_counts, shake_by_day=None, invalid_day_meal=None):
    shake_by_day = shake_by_day or {}
    weekly = {}
    for day in WEEK_DAYS:
        rows = []
        for meal_number in range(1, int(meal_counts.get(day, 5)) + 1):
            if invalid_day_meal == (day, meal_number):
                rows.append(invalid_meal_payload())
            elif shake_by_day.get(day) == meal_number:
                rows.append({"meal_type": "protein_shake", "is_protein_shake": True})
            else:
                rows.append(normal_meal_payload())
        weekly[day] = rows
    return {"weekly_days": weekly}


class ProteinShakeFoodPreferenceTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.User = get_user_model()
        MealComboTemplate.objects.create(combo_id=1)

    def create_client(self, email, protein_shake, meal_counts=None):
        meal_counts = meal_counts or {day: 5 for day in WEEK_DAYS}
        user = self.User.objects.create_user(username=email, email=email, password="pass12345", role="client")
        ClientProfile.objects.create(
            user=user,
            offer_code="food_plan_monthly",
            billing_cycle="monthly",
            includes_food_plan=True,
            includes_coaching=False,
            sale_channel="dta_direct",
        )
        answers = {
            "gender": "male",
            "height": {"unit": "cm", "value": 180},
            "weight": {"unit": "lbs", "value": 180},
            "date_of_birth": "1990-01-01",
            "goal": "maintain",
            "lifestyle": "moderate",
            "meal_plan_type": "standard",
            "workout_days": ["monday", "tuesday"],
            "meal_schedule": {"mode": "custom", "default_meals": meal_counts["sunday"], "days": meal_counts},
            "training_schedule": {"monday": "before_meal_3", "tuesday": "before_meal_2"},
            "protein_shake": protein_shake,
        }
        ClientQuestionnaireProgress.objects.create(
            user=user,
            status="completed",
            current_step="protein_shake",
            answers_json=answers,
        )
        return user

    def test_food_preferences_skip_combo_only_for_each_day_shake_meal(self):
        meal_counts = {day: 5 for day in WEEK_DAYS}
        meal_counts["tuesday"] = 4
        shake_by_day = {day: 3 for day in WEEK_DAYS}
        shake_by_day["tuesday"] = 2
        protein_shake = {
            "enabled": True,
            "counts_as_meal": True,
            "schedule_mode": "custom",
            "days": {
                day: {"enabled": True, "timing": "other", "selected_meal": meal_number}
                for day, meal_number in shake_by_day.items()
            },
        }
        user = self.create_client("shake-custom-foods@example.com", protein_shake, meal_counts=meal_counts)
        self.api.force_authenticate(user=user)

        response = self.api.put(
            "/api/v1/users/client/app/food-preferences/",
            {"builder_value": weekly_builder(meal_counts, shake_by_day=shake_by_day)},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ClientMealComboSelection.objects.filter(user=user).count(), sum(meal_counts.values()) - 7)
        self.assertFalse(ClientMealComboSelection.objects.filter(user=user, day_of_week="monday", meal_number=3).exists())
        self.assertFalse(ClientMealComboSelection.objects.filter(user=user, day_of_week="tuesday", meal_number=2).exists())

    def test_five_meals_with_valid_other_shake_persists_four_normal_combos_per_day(self):
        meal_counts = {day: 5 for day in WEEK_DAYS}
        shake_by_day = {day: 5 for day in WEEK_DAYS}
        protein_shake = {
            "enabled": True,
            "counts_as_meal": True,
            "schedule_mode": "same",
            "default_timing": "other",
            "default_selected_meal": 5,
            "days": {day: {"enabled": True, "timing": "other", "selected_meal": 5} for day in WEEK_DAYS},
        }
        user = self.create_client("shake-save@example.com", protein_shake, meal_counts=meal_counts)
        self.api.force_authenticate(user=user)

        response = self.api.put(
            "/api/v1/users/client/app/food-preferences/",
            {"builder_value": weekly_builder(meal_counts, shake_by_day=shake_by_day)},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["saved_meal_combo_selections"], 28)
        self.assertEqual(ClientMealComboSelection.objects.filter(user=user).count(), 28)
        self.assertFalse(ClientMealComboSelection.objects.filter(user=user, meal_number=5).exists())

    def test_disabled_shake_preserves_existing_behavior(self):
        meal_counts = {day: 5 for day in WEEK_DAYS}
        user = self.create_client("shake-disabled@example.com", {"enabled": False, "counts_as_meal": True}, meal_counts=meal_counts)
        self.api.force_authenticate(user=user)

        response = self.api.put(
            "/api/v1/users/client/app/food-preferences/",
            {"builder_value": weekly_builder(meal_counts, invalid_day_meal=("monday", 3))},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["code"], "INVALID_MEAL_COMBO_SELECTIONS")
