# tests/base/base_admin_test.py

from django.test import TestCase
from adminplans.models import AdminPlan

class BaseAdminTest(TestCase):
    def setUp(self):
        AdminPlan.objects.get_or_create(
            name="adminTrial",
            defaults={
                "description": "Free Admin Trial",
                "stripe_price_id": "price_test_trial",
                "price_cents": 0
            }
        )
        AdminPlan.objects.get_or_create(
            name="adminMonthly",
            defaults={
                "description": "Monthly Plan",
                "stripe_price_id": "price_test_monthly",
                "price_cents": 2999
            }
        )
        AdminPlan.objects.get_or_create(
            name="adminQuarterly",
            defaults={
                "description": "Quarterly Plan",
                "stripe_price_id": "price_test_quarterly",
                "price_cents": 7999
            }
        )
        AdminPlan.objects.get_or_create(
            name="adminAnnual",
            defaults={
                "description": "Annual Plan",
                "stripe_price_id": "price_test_annual",
                "price_cents": 29999
            }
        )
