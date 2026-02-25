from django.test import SimpleTestCase

from users.client_area.services.pricing import (
    QuoteError,
    build_client_purchase_quote,
    entitlements_for_offer,
)


class PricingServiceTests(SimpleTestCase):
    def test_premium_offer_entitlements_enable_coaching_features(self):
        entitlements = entitlements_for_offer(offer_code="food_plan_monthly_premium", coaching_term="none")
        self.assertTrue(entitlements["includes_food_plan"])
        self.assertTrue(entitlements["includes_coaching"])
        self.assertTrue(entitlements["has_premium_dashboard"])
        self.assertTrue(entitlements["can_message_coach"])

    def test_standard_offer_with_coaching_addon_enables_premium_dashboard_preview(self):
        entitlements = entitlements_for_offer(offer_code="food_plan_monthly", coaching_term="1_month")
        self.assertTrue(entitlements["includes_coaching"])
        self.assertTrue(entitlements["has_premium_dashboard"])

    def test_quote_without_discount_subscription(self):
        quote = build_client_purchase_quote(
            email="dev@example.com",
            offer_code="food_plan_monthly",
            coaching_term="none",
            sale_channel="dta_direct",
            purchase_mode="subscription",
            trial_eligible=False,
        )
        self.assertEqual(quote["amounts"]["subtotal_cents"], 1500)
        self.assertEqual(quote["amounts"]["discount_cents"], 0)
        self.assertEqual(quote["amounts"]["total_cents"], 1500)

    def test_invalid_purchase_mode_raises(self):
        with self.assertRaises(QuoteError):
            build_client_purchase_quote(
                email="dev@example.com",
                offer_code="food_plan_monthly",
                coaching_term="none",
                sale_channel="dta_direct",
                purchase_mode="invalid",
                trial_eligible=False,
            )
