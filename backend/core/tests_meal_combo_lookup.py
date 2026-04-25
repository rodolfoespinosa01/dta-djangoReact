from django.test import TestCase

from core.models import FoodLibraryItem, MealComboTemplate
from core.services.meal_combo_lookup import find_meal_combo_id_by_slots, normalize_slots_to_supported_combo_values


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
