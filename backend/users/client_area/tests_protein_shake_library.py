from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from core.models import FoodLibraryItem, MealComboTemplate, ProteinShakeIngredientSlot, ProteinShakeTemplate
from users.client_area.models import (
    ClientFoodOverride,
    ClientProteinShakeIngredientSelection,
    ClientProteinShakePreference,
)


class ProteinShakeLibraryModelTests(TestCase):
    def test_protein_shake_template_can_be_created(self):
        template = ProteinShakeTemplate.objects.create(
            name="Chocolate Protein Shake",
            slug="chocolate-protein-shake",
            default_scoop_count=1,
            min_scoop_count=1,
            max_scoop_count=2,
        )

        self.assertEqual(str(template), "Chocolate Protein Shake")

    def test_slots_can_be_attached_to_template(self):
        template = ProteinShakeTemplate.objects.create(name="Slot Test Shake", slug="slot-test-shake")
        item = FoodLibraryItem.objects.create(
            source_food_id=910001,
            name="Test Protein Powder STANDARD",
            category="Test Protein Powder STANDARD",
            macro=FoodLibraryItem.Macro.PROTEIN,
            protein=24,
        )
        ProteinShakeIngredientSlot.objects.create(
            template=template,
            slot_key=ProteinShakeIngredientSlot.SlotKey.PROTEIN_POWDER,
            display_name="Protein Powder",
            required=True,
            allow_exclude=False,
            macro_role=ProteinShakeIngredientSlot.MacroRole.PROTEIN,
            default_food_library_item=item,
        )

        self.assertEqual(template.ingredient_slots.count(), 1)
        self.assertEqual(template.ingredient_slots.get().default_food_library_item, item)

    def test_first_seeded_template_exists(self):
        template = ProteinShakeTemplate.objects.get(slug="banana-peanut-butter-protein-shake")

        self.assertEqual(template.name, "Banana Peanut Butter Protein Shake")
        self.assertEqual(template.ingredient_slots.count(), 5)
        self.assertTrue(template.ingredient_slots.get(slot_key="protein_powder").required)

    def test_required_protein_powder_slot_cannot_be_excluded(self):
        user = get_user_model().objects.create_user(
            username="shake-model@example.com",
            email="shake-model@example.com",
            password="pass12345",
            role="client",
        )
        template = ProteinShakeTemplate.objects.get(slug="banana-peanut-butter-protein-shake")
        preference = ClientProteinShakePreference.objects.create(user=user, template=template)
        selection = ClientProteinShakeIngredientSelection(
            preference=preference,
            slot=template.ingredient_slots.get(slot_key="protein_powder"),
            excluded=True,
        )

        with self.assertRaises(ValidationError):
            selection.full_clean()

    def test_existing_meal_combo_library_behavior_is_unchanged(self):
        combo = MealComboTemplate.objects.create(
            combo_id=990001,
            protein_slot_1="Ground Beef STANDARD",
            protein_slot_2="-",
            carb_slot_1="White Rice STANDARD",
            carb_slot_2="-",
            fat_slot_1="Avocado STANDARD",
            fat_slot_2="-",
        )

        self.assertEqual(MealComboTemplate.objects.get(combo_id=990001), combo)
        self.assertEqual(combo.protein_slot_1, "Ground Beef STANDARD")


class ProteinShakeLibraryApiTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.User = get_user_model()
        self.user = self.User.objects.create_user(
            username="shake-client@example.com",
            email="shake-client@example.com",
            password="pass12345",
            role="client",
        )
        self.api.force_authenticate(user=self.user)
        self.template = ProteinShakeTemplate.objects.get(slug="banana-peanut-butter-protein-shake")

    def test_fetch_active_templates_api_returns_expected_slots(self):
        response = self.api.get("/api/v1/users/client/app/protein-shakes/templates/")

        self.assertEqual(response.status_code, 200)
        templates = response.data["protein_shake_templates"]
        seeded = next(row for row in templates if row["slug"] == "banana-peanut-butter-protein-shake")
        self.assertEqual(seeded["name"], "Banana Peanut Butter Protein Shake")
        self.assertEqual(
            [slot["slot_key"] for slot in seeded["ingredient_slots"]],
            ["protein_powder", "liquid", "carb", "fat_addin", "sweetener"],
        )
        standard_names = {row["name"] for row in response.data["protein_shake_standard_items"]}
        self.assertIn("Water STANDARD", standard_names)
        self.assertIn("Protein Powder STANDARD", standard_names)

    def test_save_user_shake_selection_without_scoop_count_works_and_optional_slots_can_be_excluded(self):
        carb_slot = self.template.ingredient_slots.get(slot_key="carb")
        response = self.api.put(
            "/api/v1/users/client/app/protein-shakes/preference/",
            {
                "template_slug": self.template.slug,
                "enabled": True,
                "ingredient_selections": [
                    {"slot_key": "carb", "excluded": True, "serving_amount": "0", "serving_unit": ""},
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        preference = ClientProteinShakePreference.objects.get(user=self.user, template=self.template)
        self.assertIsNone(preference.scoop_count)
        selection = preference.ingredient_selections.get(slot=carb_slot)
        self.assertTrue(selection.excluded)

    def test_old_payload_with_scoop_count_still_succeeds(self):
        response = self.api.put(
            "/api/v1/users/client/app/protein-shakes/preference/",
            {
                "template_slug": self.template.slug,
                "enabled": True,
                "scoop_count": 2,
                "ingredient_selections": [],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        preference = ClientProteinShakePreference.objects.get(user=self.user, template=self.template)
        self.assertEqual(preference.scoop_count, 2)
        self.assertEqual(response.data["protein_shake_preference"]["scoop_count"], 2)

    def test_required_protein_powder_slot_cannot_be_excluded_via_api(self):
        response = self.api.put(
            "/api/v1/users/client/app/protein-shakes/preference/",
            {
                "template_slug": self.template.slug,
                "ingredient_selections": [{"slot_key": "protein_powder", "excluded": True}],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["code"], "REQUIRED_SLOT_CANNOT_BE_EXCLUDED")

    def test_user_selection_can_store_branded_protein_powder_product(self):
        override = ClientFoodOverride.objects.create(
            user=self.user,
            canonical_category="Protein Powder STANDARD",
            external_provider="open_food_facts",
            source_type=ClientFoodOverride.SOURCE_TYPE_OPEN_FOOD_FACTS,
            external_food_id="737628064502",
            barcode="737628064502",
            display_name="Brand Whey Protein",
            brand_name="Brand",
            serving_size=Decimal("32"),
            serving_unit="g",
            serving_weight_grams=Decimal("32"),
            protein=Decimal("24"),
            carbs=Decimal("3"),
            fats=Decimal("2"),
            calories=Decimal("126"),
            raw_payload={"barcode": "737628064502"},
        )

        response = self.api.put(
            "/api/v1/users/client/app/protein-shakes/preference/",
            {
                "template_slug": self.template.slug,
                "ingredient_selections": [
                    {
                        "slot_key": "protein_powder",
                        "selected_food_override_id": override.id,
                        "serving_amount": "1",
                        "serving_unit": "scoop",
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        selection = ClientProteinShakeIngredientSelection.objects.get(
            preference__user=self.user,
            slot__slot_key="protein_powder",
        )
        self.assertEqual(selection.selected_food_override, override)

    def test_water_liquid_slot_maps_to_zero_macro_standard_item(self):
        water = FoodLibraryItem.objects.get(name="Water STANDARD")
        self.assertEqual(water.protein, 0)
        self.assertEqual(water.carbs, 0)
        self.assertEqual(water.fats, 0)

        response = self.api.put(
            "/api/v1/users/client/app/protein-shakes/preference/",
            {
                "template_slug": self.template.slug,
                "ingredient_selections": [
                    {
                        "slot_key": "liquid",
                        "selected_food_library_item_id": water.id,
                        "serving_amount": "1",
                        "serving_unit": "cup",
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        selection = ClientProteinShakeIngredientSelection.objects.get(
            preference__user=self.user,
            slot__slot_key="liquid",
        )
        self.assertEqual(selection.selected_food_library_item, water)
