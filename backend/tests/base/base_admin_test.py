# tests/base/base_admin_test.py

from django.test import TestCase
from adminplans.models import AdminPlan

class BaseAdminTest(TestCase):
    def setUp(self):
        AdminPlan.objects.create(
            name="adminTrial",
            description="Free Admin Trial",
            stripe_price_id="price_test_trial",
            price_cents=0
        )
        AdminPlan.objects.create(
            name="adminMonthly",
            description="Monthly Plan",
            stripe_price_id="price_test_monthly",
            price_cents=2999
        )
        AdminPlan.objects.create(
            name="adminQuarterly",
            description="Quarterly Plan",
            stripe_price_id="price_test_quarterly",
            price_cents=7999
        )
        AdminPlan.objects.create(
            name="adminAnnual",
            description="Annual Plan",
            stripe_price_id="price_test_annual",
            price_cents=29999
        )
