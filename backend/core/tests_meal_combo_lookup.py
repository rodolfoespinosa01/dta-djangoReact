from django.test import TestCase

from core.models import FoodLibraryItem, MealComboTemplate
from core.services.meal_combo_lookup import (
    find_meal_combo_id_by_slots,
    normalize_slots_to_supported_combo_values,
)
from core.services.meal_combo_shape_policy import select_meal_combo_template_for_target


class MealComboLookupNormalizationTests(TestCase):
    def setUp(self):
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
                    category="Fats",
                    name="Avocado",
                    measurement_unit="oz",
                    protein=1,
                    carbs=4,
                    fats=7,
                ),
                FoodLibraryItem(
                    source_food_id=3,
                    category="Oil STANDARD",
                    name="Olive Oil",
                    measurement_unit="oz",
                    protein=0,
                    carbs=0,
                    fats=14,
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

    def test_lookup_requires_exact_combo_slot_values(self):
        combo_id = find_meal_combo_id_by_slots(
            protein_1="Ground Beef 95/5",
            protein_2="-",
            carbs_1="White Rice",
            carbs_2="-",
            fats_1="Avocado",
            fats_2="Olive Oil",
        )

        self.assertIsNone(combo_id)

    def test_lookup_resolves_canonical_combo_slot_values(self):
        combo_id = find_meal_combo_id_by_slots(
            protein_1="Ground Beef STANDARD",
            protein_2="-",
            carbs_1="White Rice",
            carbs_2="-",
            fats_1="Avocado",
            fats_2="Oil STANDARD",
        )

        self.assertEqual(combo_id, 501)

    def test_saved_payload_normalization_can_repair_legacy_food_names(self):
        normalized = normalize_slots_to_supported_combo_values(
            {
                "protein_1": "Ground Beef 95/5",
                "protein_2": "-",
                "carbs_1": "White Rice",
                "carbs_2": "-",
                "fats_1": "Avocado",
                "fats_2": "Olive Oil",
            }
        )

        self.assertEqual(normalized["protein_1"], "Ground Beef STANDARD")
        self.assertEqual(normalized["fats_2"], "Oil STANDARD")


class MealComboShapePolicyTests(TestCase):
    def setUp(self):
        self.one_protein_one_carb = MealComboTemplate.objects.create(
            combo_id=1001,
            protein_slot_1="Chicken Breast",
            protein_slot_2="-",
            carb_slot_1="White Rice",
            carb_slot_2="-",
            fat_slot_1="Avocado",
            fat_slot_2="Oil STANDARD",
        )
        self.two_protein_one_carb = MealComboTemplate.objects.create(
            combo_id=1002,
            protein_slot_1="Chicken Breast",
            protein_slot_2="Steak STANDARD",
            carb_slot_1="White Rice",
            carb_slot_2="-",
            fat_slot_1="Avocado",
            fat_slot_2="Oil STANDARD",
        )
        self.one_protein_two_carb = MealComboTemplate.objects.create(
            combo_id=1003,
            protein_slot_1="Chicken Breast",
            protein_slot_2="-",
            carb_slot_1="White Rice",
            carb_slot_2="Banana",
            fat_slot_1="Avocado",
            fat_slot_2="Oil STANDARD",
        )
        self.two_protein_two_carb = MealComboTemplate.objects.create(
            combo_id=1004,
            protein_slot_1="Chicken Breast",
            protein_slot_2="Steak STANDARD",
            carb_slot_1="White Rice",
            carb_slot_2="Banana",
            fat_slot_1="Avocado",
            fat_slot_2="Oil STANDARD",
        )
        self.selected_slots = {
            "protein_1": "Chicken Breast",
            "protein_2": "Steak STANDARD",
            "carbs_1": "White Rice",
            "carbs_2": "Banana",
            "fats_1": "Avocado",
            "fats_2": "Oil STANDARD",
        }

    def _select(self, *, protein, carbs, training_adjacent=False, saved_combo=None):
        return select_meal_combo_template_for_target(
            saved_combo=saved_combo or self.two_protein_two_carb,
            meal_target={"protein": protein, "carbs": carbs, "fats": 15},
            is_training_adjacent=training_adjacent,
            selected_slots=self.selected_slots,
        )

    def test_meal_with_40g_protein_prefers_one_protein_combo(self):
        decision = self._select(protein=40, carbs=65)

        self.assertEqual(decision.combo.protein_slot_2, "-")
        self.assertEqual(decision.preferred_shape.protein_structure, "one_protein")

    def test_meal_with_55g_protein_allows_two_protein_combo(self):
        decision = self._select(protein=55, carbs=65, saved_combo=self.two_protein_two_carb)

        self.assertTrue(decision.preferred_shape.allows_second_protein)
        self.assertEqual(decision.preferred_shape.protein_structure, "one_or_two_protein")

    def test_meal_with_35g_carbs_and_no_training_prefers_one_carb_combo(self):
        decision = self._select(protein=55, carbs=35, training_adjacent=False)

        self.assertEqual(decision.combo.carb_slot_2, "-")
        self.assertEqual(decision.preferred_shape.carb_structure, "one_carb")

    def test_meal_with_50g_carbs_and_training_adjacent_allows_two_carb_combo(self):
        decision = self._select(protein=55, carbs=50, training_adjacent=True)

        self.assertTrue(decision.preferred_shape.allows_second_carb)
        self.assertEqual(decision.preferred_shape.carb_structure, "one_or_two_carb")

    def test_meal_with_65g_carbs_allows_two_carb_combo(self):
        decision = self._select(protein=40, carbs=65, training_adjacent=False)

        self.assertTrue(decision.preferred_shape.allows_second_carb)
        self.assertEqual(decision.preferred_shape.carb_structure, "one_or_two_carb")

    def test_no_ideal_combo_falls_back_to_valid_combo(self):
        MealComboTemplate.objects.exclude(combo_id=1004).delete()

        decision = self._select(protein=40, carbs=35, training_adjacent=False, saved_combo=self.two_protein_two_carb)

        self.assertEqual(decision.combo.combo_id, 1004)
        self.assertIsNotNone(decision.fallback_reason)
