from decimal import Decimal
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from core.models import FoodLibraryItem, MealComboTemplate
from core.services.product_search import ProductSearchError
from users.client_area.models import (
    ClientFoodOverride,
    ClientMealComboSelection,
    ClientMealPlanGeneratedMeal,
    ClientMealPlanGenerationJob,
    ClientMealPlanGenerationStep1Row,
    ProductImageSubmission,
)
from users.client_area.services.meal_plan_generation.pipeline import run_steps_2_to_10_for_day
from users.client_area.services.meal_plan_generation.runner import get_generated_meal_day_detail


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
            "provider": "usda",
            "provider_product_id": "123",
            "fdc_id": "123",
            "barcode": "012345678905",
            "image_url": "",
            "display_name": "Walmart - Ground Beef 93/7",
            "brand_name": "Walmart",
            "ingredients": "",
            "serving_size": Decimal("112"),
            "serving_unit": "g",
            "serving_weight_grams": Decimal("112"),
            "protein": Decimal("5.821"),
            "carbs": Decimal("0"),
            "fats": Decimal("2.025"),
            "calories": Decimal("43.00"),
            "raw_payload": {"fdcId": 123},
        }

        with patch("users.client_area.views.food_overrides.get_product_details", return_value=details):
            response = self.api.post(
                "/api/v1/users/client/app/food-overrides/save/",
                {"canonical_category": "Ground Beef STANDARD", "provider": "usda", "provider_product_id": "123"},
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        saved = response.data["food_override"]
        self.assertEqual(saved["canonical_category"], "Ground Beef STANDARD")
        self.assertEqual(saved["external_provider"], "usda")
        self.assertEqual(saved["external_food_id"], "123")
        self.assertEqual(saved["barcode"], "012345678905")

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

    def test_combined_product_search_returns_open_food_facts_and_usda_shape(self):
        self.api.force_authenticate(user=self.user)
        with patch("users.client_area.views.food_overrides.search_products") as search:
            search.return_value = {
                "foods": [
                    {
                        "provider": "open_food_facts",
                        "provider_product_id": "737628064502",
                        "barcode": "737628064502",
                        "display_name": "Protein Oats",
                        "brand_name": "Brand",
                        "serving_size": Decimal("40"),
                        "serving_unit": "40 g",
                        "serving_weight_grams": Decimal("40"),
                        "protein": Decimal("5"),
                        "carbs": Decimal("10"),
                        "fats": Decimal("2"),
                        "calories": Decimal("80"),
                        "image_url": "https://example.com/product.jpg",
                        "ingredients": "Oats",
                    }
                ],
                "page": 1,
                "page_size": 12,
                "providers": ["open_food_facts", "usda"],
                "errors": {},
            }

            response = self.api.post(
                "/api/v1/users/client/app/food-overrides/products/search/",
                {"query": "oats"},
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        product = response.data["products"][0]
        self.assertEqual(product["provider"], "open_food_facts")
        self.assertEqual(product["barcode"], "737628064502")
        self.assertEqual(product["image_url"], "https://example.com/product.jpg")

    def test_barcode_lookup_returns_open_food_facts_product(self):
        self.api.force_authenticate(user=self.user)
        with patch("users.client_area.views.food_overrides.lookup_barcode") as lookup:
            lookup.return_value = {
                "provider": "open_food_facts",
                "provider_product_id": "737628064502",
                "barcode": "737628064502",
                "display_name": "Protein Oats",
                "brand_name": "Brand",
                "serving_size": Decimal("40"),
                "serving_unit": "40 g",
                "serving_weight_grams": Decimal("40"),
                "protein": Decimal("5"),
                "carbs": Decimal("10"),
                "fats": Decimal("2"),
                "calories": Decimal("80"),
                "image_url": "https://example.com/product.jpg",
                "ingredients": "Oats",
            }

            response = self.api.post(
                "/api/v1/users/client/app/food-overrides/products/barcode/",
                {"barcode": "737628064502"},
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["product"]["provider"], "open_food_facts")
        self.assertEqual(response.data["product"]["image_url"], "https://example.com/product.jpg")

    def test_barcode_lookup_not_found_returns_stable_json_error(self):
        self.api.force_authenticate(user=self.user)
        with patch("users.client_area.views.food_overrides.lookup_barcode", return_value=None):
            response = self.api.post(
                "/api/v1/users/client/app/food-overrides/products/barcode/",
                {"barcode": "000000000000"},
                format="json",
            )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"]["code"], "PRODUCT_NOT_FOUND")
        self.assertIn("Product not found", response.data["error"]["message"])

    def test_product_search_provider_failure_returns_stable_json_error(self):
        self.api.force_authenticate(user=self.user)
        with patch("users.client_area.views.food_overrides.search_products", side_effect=ProductSearchError("boom")):
            response = self.api.post(
                "/api/v1/users/client/app/food-overrides/products/search/",
                {"query": "chicken breast"},
                format="json",
            )

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.data["error"]["code"], "PRODUCT_SEARCH_FAILED")

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_product_with_no_provider_image_returns_no_image_url(self):
        self.api.force_authenticate(user=self.user)
        with patch("users.client_area.views.food_overrides.search_products") as search:
            search.return_value = {
                "foods": [
                    {
                        "provider": "open_food_facts",
                        "provider_product_id": "737628064502",
                        "barcode": "737628064502",
                        "display_name": "Protein Oats",
                        "brand_name": "Brand",
                        "serving_size": Decimal("40"),
                        "serving_unit": "40 g",
                        "serving_weight_grams": Decimal("40"),
                        "protein": Decimal("5"),
                        "carbs": Decimal("10"),
                        "fats": Decimal("2"),
                        "calories": Decimal("80"),
                        "image_url": "",
                        "ingredients": "Oats",
                    }
                ],
                "page": 1,
                "page_size": 12,
                "providers": ["open_food_facts"],
                "errors": {},
            }

            response = self.api.post(
                "/api/v1/users/client/app/food-overrides/products/search/",
                {"query": "oats"},
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        product = response.data["products"][0]
        self.assertEqual(product["image_url"], "")
        self.assertEqual(product["image_source"], "")

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_client_image_upload_creates_pending_submission(self):
        self.api.force_authenticate(user=self.user)
        image = SimpleUploadedFile("product.jpg", b"fake-image", content_type="image/jpeg")

        response = self.api.post(
            "/api/v1/users/client/app/food-overrides/products/images/submit/",
            {
                "provider": "open_food_facts",
                "provider_product_id": "737628064502",
                "barcode": "737628064502",
                "product_name": "Protein Oats",
                "brand": "Brand",
                "image": image,
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        submission = ProductImageSubmission.objects.get()
        self.assertEqual(submission.status, ProductImageSubmission.Status.PENDING)
        self.assertEqual(submission.submitted_by, self.user)
        self.assertEqual(response.data["image_submission"]["status"], "pending")

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_pending_image_is_only_marked_for_submitting_user(self):
        ProductImageSubmission.objects.create(
            submitted_by=self.user,
            provider="open_food_facts",
            provider_product_id="737628064502",
            barcode="737628064502",
            product_name="Protein Oats",
            brand="Brand",
            image=SimpleUploadedFile("pending.jpg", b"fake-image", content_type="image/jpeg"),
            status=ProductImageSubmission.Status.PENDING,
        )
        product_payload = {
            "foods": [
                {
                    "provider": "open_food_facts",
                    "provider_product_id": "737628064502",
                    "barcode": "737628064502",
                    "display_name": "Protein Oats",
                    "brand_name": "Brand",
                    "image_url": "",
                }
            ],
            "page": 1,
            "page_size": 12,
            "providers": ["open_food_facts"],
            "errors": {},
        }

        with patch("users.client_area.views.food_overrides.search_products", return_value=product_payload):
            self.api.force_authenticate(user=self.user)
            own_response = self.api.post(
                "/api/v1/users/client/app/food-overrides/products/search/",
                {"query": "oats"},
                format="json",
            )
            self.api.force_authenticate(user=self.other_user)
            other_response = self.api.post(
                "/api/v1/users/client/app/food-overrides/products/search/",
                {"query": "oats"},
                format="json",
            )

        self.assertEqual(own_response.data["products"][0]["image_submission_status"], "pending")
        self.assertEqual(other_response.data["products"][0]["image_submission_status"], "")

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_approved_image_overrides_provider_image_in_search_results(self):
        ProductImageSubmission.objects.create(
            submitted_by=self.user,
            provider="open_food_facts",
            provider_product_id="737628064502",
            barcode="737628064502",
            product_name="Protein Oats",
            brand="Brand",
            image=SimpleUploadedFile("approved.jpg", b"fake-image", content_type="image/jpeg"),
            status=ProductImageSubmission.Status.APPROVED,
        )
        self.api.force_authenticate(user=self.other_user)
        with patch("users.client_area.views.food_overrides.search_products") as search:
            search.return_value = {
                "foods": [
                    {
                        "provider": "open_food_facts",
                        "provider_product_id": "737628064502",
                        "barcode": "737628064502",
                        "display_name": "Protein Oats",
                        "brand_name": "Brand",
                        "image_url": "https://provider.example/image.jpg",
                    }
                ],
                "page": 1,
                "page_size": 12,
                "providers": ["open_food_facts"],
                "errors": {},
            }

            response = self.api.post(
                "/api/v1/users/client/app/food-overrides/products/search/",
                {"query": "oats"},
                format="json",
            )

        product = response.data["products"][0]
        self.assertEqual(product["image_source"], "approved_local")
        self.assertIn("/media/product_image_submissions/", product["image_url"])
        self.assertEqual(product["provider_image_url"], "https://provider.example/image.jpg")

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_rejected_image_does_not_display_publicly(self):
        ProductImageSubmission.objects.create(
            submitted_by=self.user,
            provider="open_food_facts",
            provider_product_id="737628064502",
            barcode="737628064502",
            image=SimpleUploadedFile("rejected.jpg", b"fake-image", content_type="image/jpeg"),
            status=ProductImageSubmission.Status.REJECTED,
        )
        self.api.force_authenticate(user=self.user)
        with patch("users.client_area.views.food_overrides.search_products") as search:
            search.return_value = {
                "foods": [
                    {
                        "provider": "open_food_facts",
                        "provider_product_id": "737628064502",
                        "barcode": "737628064502",
                        "display_name": "Protein Oats",
                        "brand_name": "Brand",
                        "image_url": "",
                    }
                ],
                "page": 1,
                "page_size": 12,
                "providers": ["open_food_facts"],
                "errors": {},
            }

            response = self.api.post(
                "/api/v1/users/client/app/food-overrides/products/search/",
                {"query": "oats"},
                format="json",
            )

        product = response.data["products"][0]
        self.assertEqual(product["image_url"], "")
        self.assertEqual(product["image_submission_status"], "")

    def test_open_food_facts_override_saves_provider_source_barcode_and_image(self):
        self.api.force_authenticate(user=self.user)
        details = {
            "provider": "open_food_facts",
            "provider_product_id": "737628064502",
            "barcode": "737628064502",
            "display_name": "Protein Oats",
            "brand_name": "Brand",
            "serving_size": Decimal("40"),
            "serving_unit": "40 g",
            "serving_weight_grams": Decimal("40"),
            "protein": Decimal("5"),
            "carbs": Decimal("10"),
            "fats": Decimal("2"),
            "calories": Decimal("80"),
            "image_url": "https://example.com/product.jpg",
            "ingredients": "Oats",
            "raw_payload": {"code": "737628064502"},
        }

        with patch("users.client_area.views.food_overrides.get_product_details", return_value=details):
            response = self.api.post(
                "/api/v1/users/client/app/food-overrides/save/",
                {
                    "canonical_category": "Ground Beef STANDARD",
                    "provider": "open_food_facts",
                    "provider_product_id": "737628064502",
                },
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        saved = response.data["food_override"]
        self.assertEqual(saved["external_provider"], "open_food_facts")
        self.assertEqual(saved["provider_product_id"], "737628064502")
        self.assertEqual(saved["barcode"], "737628064502")
        self.assertEqual(saved["image_url"], "https://example.com/product.jpg")

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
            preparation_state=FoodLibraryItem.PreparationState.COOKED,
            measurement_basis_label="Measure cooked",
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

    def test_day_detail_returns_override_image_and_measurement_basis(self):
        ClientFoodOverride.objects.create(
            user=self.user,
            canonical_category="Chicken Breast STANDARD",
            external_provider="open_food_facts",
            external_food_id="123456",
            display_name="Brand Chicken",
            brand_name="Brand",
            barcode="123456",
            image_url="https://example.com/chicken.jpg",
            protein=Decimal("10.00000"),
            carbs=0,
            fats=0,
            calories=0,
            preparation_state=ClientFoodOverride.PreparationState.AS_PACKAGED,
            measurement_basis_label="As packaged",
        )
        self._run_generation()

        detail = get_generated_meal_day_detail(self.user, "sunday")
        slot = detail["meals"][0]["slots"]["protein_1"]

        self.assertEqual(slot["name"], "Brand Chicken")
        self.assertEqual(slot["image_url"], "https://example.com/chicken.jpg")
        self.assertEqual(slot["image_source"], "selected_product")
        self.assertEqual(slot["measurement_basis_label"], "As packaged")
        self.assertEqual(slot["preparation_state"], "as_packaged")

    def test_day_detail_returns_generic_measurement_basis_for_standard_food(self):
        self._run_generation()

        detail = get_generated_meal_day_detail(self.user, "sunday")
        slot = detail["meals"][0]["slots"]["protein_1"]

        self.assertEqual(slot["canonical_name"], "Chicken Breast STANDARD")
        self.assertEqual(slot["image_url"], "")
        self.assertEqual(slot["measurement_basis_label"], "Measure cooked")
        self.assertEqual(slot["preparation_state"], "cooked")
