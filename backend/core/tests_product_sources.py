from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from core.services.product_search import lookup_barcode
from core.services.product_sources.open_food_facts import normalize_product, search_products


class OpenFoodFactsProviderTests(TestCase):
    def test_normalize_product_maps_image_barcode_and_macros_per_oz(self):
        product = normalize_product(
            {
                "code": "737628064502",
                "product_name": "Protein Oats",
                "brands": "Example Brand",
                "serving_size": "40 g",
                "serving_quantity": 40,
                "image_front_url": "https://images.openfoodfacts.org/product.jpg",
                "ingredients_text": "Oats, whey protein.",
                "nutriments": {
                    "proteins_100g": 20,
                    "carbohydrates_100g": 50,
                    "fat_100g": 8,
                    "energy-kcal_100g": 360,
                },
            }
        )

        self.assertEqual(product["provider"], "open_food_facts")
        self.assertEqual(product["barcode"], "737628064502")
        self.assertEqual(product["image_url"], "https://images.openfoodfacts.org/product.jpg")
        self.assertEqual(product["ingredients"], "Oats, whey protein.")
        self.assertEqual(product["protein"], Decimal("5.66990"))
        self.assertEqual(product["carbs"], Decimal("14.17475"))
        self.assertEqual(product["fats"], Decimal("2.26796"))
        self.assertEqual(product["calories"], Decimal("102.05820"))

    def test_search_products_normalizes_open_food_facts_response(self):
        with patch("core.services.product_sources.open_food_facts._request") as request:
            request.return_value = {
                "count": 1,
                "page": 1,
                "page_count": 1,
                "products": [
                    {
                        "code": "123",
                        "product_name": "Almond Milk",
                        "brands": "Brand",
                        "image_url": "https://example.com/almond.jpg",
                        "nutriments": {"proteins_100g": 1, "carbohydrates_100g": 2, "fat_100g": 3},
                    }
                ],
            }

            result = search_products("almond milk", page=1, page_size=5)

        self.assertEqual(result["foods"][0]["provider"], "open_food_facts")
        self.assertEqual(result["foods"][0]["image_url"], "https://example.com/almond.jpg")
        self.assertEqual(request.call_args.kwargs["params"]["search_terms"], "almond milk")

    def test_barcode_lookup_normalizes_found_product(self):
        with patch("core.services.product_sources.open_food_facts._request") as request:
            request.return_value = {
                "status": 1,
                "product": {
                    "code": "123456789012",
                    "product_name": "Greek Yogurt",
                    "image_front_url": "https://example.com/yogurt.jpg",
                    "nutriments": {"proteins_100g": 10},
                },
            }

            product = lookup_barcode("123456789012")

        self.assertEqual(product["provider"], "open_food_facts")
        self.assertEqual(product["barcode"], "123456789012")
        self.assertEqual(product["image_url"], "https://example.com/yogurt.jpg")

    def test_barcode_lookup_uses_v2_route_without_json_suffix(self):
        with patch("core.services.product_sources.open_food_facts._request") as request:
            request.return_value = {"status": 0}

            product = lookup_barcode("123456789012")

        self.assertIsNone(product)
        self.assertEqual(request.call_args_list[0].args[0], "api/v2/product/123456789012")

    def test_barcode_lookup_falls_back_to_legacy_json_route(self):
        with patch("core.services.product_sources.open_food_facts._request") as request:
            request.side_effect = [
                {"status": 0},
                {
                    "status": 1,
                    "product": {
                        "code": "123456789012",
                        "product_name": "Greek Yogurt",
                        "nutriments": {"proteins_100g": 10},
                    },
                },
            ]

            product = lookup_barcode("123456789012")

        self.assertEqual(product["barcode"], "123456789012")
        self.assertEqual(request.call_args_list[1].args[0], "api/v0/product/123456789012.json")
