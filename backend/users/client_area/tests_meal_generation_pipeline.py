from decimal import Decimal

from django.test import TestCase

from core.models import FoodLibraryItem, MealComboTemplate
from users.client_area.services.meal_plan_generation.pipeline import _evaluate_candidate, _food_macros_by_name


class StubStep1Row:
    error_code = 1
    pro_negative = Decimal("40")
    carbs_negative = Decimal("60")
    fats_negative = Decimal("20")


class MealGenerationPipelineFoodMappingTests(TestCase):
    def setUp(self):
        FoodLibraryItem.objects.bulk_create(
            [
                FoodLibraryItem(
                    source_food_id=10,
                    category="Chicken Breast",
                    name="Chicken Breast",
                    macro="Protein",
                    protein=Decimal("6.55"),
                    carbs=0,
                    fats=Decimal("1.00"),
                    is_placeholder=True,
                ),
                FoodLibraryItem(
                    source_food_id=42,
                    category="White Rice",
                    name="White Rice",
                    macro="Carbs",
                    protein=Decimal("2.00"),
                    carbs=Decimal("22.70"),
                    fats=Decimal("0.20"),
                    is_placeholder=True,
                ),
                FoodLibraryItem(
                    source_food_id=71,
                    category="Avocado",
                    name="Avocado",
                    macro="Fats",
                    protein=Decimal("0.60"),
                    carbs=Decimal("2.42"),
                    fats=Decimal("4.16"),
                    is_placeholder=True,
                ),
                FoodLibraryItem(
                    source_food_id=1,
                    category="Ground Beef STANDARD",
                    name="Ground Beef 95/5",
                    macro="Protein",
                    protein=Decimal("6.00"),
                    carbs=0,
                    fats=Decimal("1.683"),
                    is_placeholder=False,
                ),
            ]
        )

    def test_food_map_uses_macro_bearing_canonical_placeholder_rows(self):
        foods = _food_macros_by_name(["Chicken Breast", "White Rice", "Avocado"])

        self.assertEqual(foods["chicken breast"].name, "Chicken Breast")
        self.assertEqual(foods["white rice"].name, "White Rice")
        self.assertEqual(foods["avocado"].name, "Avocado")

    def test_food_map_still_maps_combo_category_to_first_real_variation(self):
        foods = _food_macros_by_name(["Ground Beef STANDARD"])

        self.assertEqual(foods["ground beef standard"].name, "Ground Beef 95/5")

    def test_candidate_amounts_are_nonzero_for_macro_bearing_combo_slots(self):
        combo = MealComboTemplate.objects.create(
            combo_id=9001,
            protein_slot_1="Chicken Breast",
            protein_slot_2="-",
            carb_slot_1="White Rice",
            carb_slot_2="-",
            fat_slot_1="Avocado",
            fat_slot_2="-",
            protein_split_1=Decimal("1.00"),
            protein_split_2=Decimal("0.00"),
            carb_split_1=Decimal("1.00"),
            carb_split_2=Decimal("0.00"),
            fat_split_1=Decimal("1.00"),
            fat_split_2=Decimal("0.00"),
        )
        foods = _food_macros_by_name(["Chicken Breast", "White Rice", "Avocado"])

        candidate = _evaluate_candidate(
            StubStep1Row(),
            combo,
            foods,
            {"protein": Decimal("40"), "carbs": Decimal("60"), "fats": Decimal("20")},
        )

        self.assertGreater(candidate["amounts"]["protein1"], 0)
        self.assertGreater(candidate["amounts"]["carbs1"], 0)
        self.assertGreater(candidate["amounts"]["fats1"], 0)
