from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings

from core.services.usda_fooddata import get_food_details, normalize_food, search_foods


class USDAFoodDataProviderTests(TestCase):
    def test_search_foods_normalizes_results(self):
        with patch("core.services.usda_fooddata._request") as request:
            request.return_value = {
                "currentPage": 1,
                "totalHits": 1,
                "totalPages": 1,
                "foods": [
                    {
                        "fdcId": 123,
                        "gtinUpc": "012345678905",
                        "description": "GROUND BEEF 93/7",
                        "brandOwner": "Walmart",
                        "dataType": "Branded",
                        "servingSize": 112,
                        "servingSizeUnit": "g",
                        "labelNutrients": {
                            "protein": {"value": 23},
                            "fat": {"value": 8},
                            "carbohydrates": {"value": 0},
                            "calories": {"value": 170},
                        },
                    }
                ],
            }

            result = search_foods("ground beef", page=1, page_size=10)

        self.assertEqual(result["total_hits"], 1)
        self.assertEqual(result["foods"][0]["fdc_id"], "123")
        self.assertEqual(result["foods"][0]["barcode"], "012345678905")
        self.assertEqual(result["foods"][0]["brand_name"], "Walmart")
        self.assertGreater(result["foods"][0]["protein"], Decimal("0"))
        called_kwargs = request.call_args.kwargs
        self.assertEqual(called_kwargs["json"]["dataType"], ["Branded"])

    def test_detail_parser_extracts_macro_values_per_oz(self):
        details = normalize_food(
            {
                "fdcId": 456,
                "description": "UNSWEETENED ALMOND MILK",
                "brandOwner": "Brand",
                "servingSize": 240,
                "servingSizeUnit": "ml",
                "labelNutrients": {
                    "protein": {"value": 1},
                    "fat": {"value": 2.5},
                    "carbohydrates": {"value": 1},
                    "calories": {"value": 30},
                },
            }
        )

        self.assertEqual(details["fdc_id"], "456")
        self.assertEqual(details["serving_weight_grams"], Decimal("240.0000"))
        self.assertEqual(details["protein"], Decimal("0.11812"))
        self.assertEqual(details["carbs"], Decimal("0.11812"))
        self.assertEqual(details["fats"], Decimal("0.29531"))
        self.assertEqual(details["calories"], Decimal("3.54369"))

    @override_settings(USDA_FDC_API_KEY="backend-secret-key")
    def test_get_food_details_keeps_api_key_out_of_response(self):
        with patch("core.services.usda_fooddata._request") as request:
            request.return_value = {
                "fdcId": 789,
                "description": "CHICKEN",
                "foodNutrients": [
                    {"nutrientId": 1003, "value": 31},
                    {"nutrientId": 1004, "value": 3.6},
                    {"nutrientId": 1005, "value": 0},
                    {"nutrientId": 1008, "value": 165},
                ],
            }

            details = get_food_details("789")

        self.assertNotIn("backend-secret-key", str(details))
        self.assertNotIn("api_key", str(details))
        self.assertEqual(request.call_args.args[0], "GET")
