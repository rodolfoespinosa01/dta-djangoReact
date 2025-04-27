from tests.base.base_admin_test import BaseAdminTest
from django.urls import reverse
from django.utils import timezone
from users.models import CustomUser
from adminplans.models import AdminProfile, AdminPlan
from datetime import timedelta

class SuperAdminDashboardAmountsRenderTest(BaseAdminTest):
    def setUp(self):
        super().setUp()

        # Create SuperAdmin
        self.superadmin = CustomUser.objects.create_superuser(
            username="superadmin@test.com",
            email="superadmin@test.com",
            password="superpass123"
        )

        # Create plan prices
        self.monthly_plan = AdminPlan.objects.get_or_create(
            name='adminMonthly',
            defaults={'description': 'Monthly', 'stripe_price_id': 'price1', 'price_cents': 3000}
        )[0]
        self.annual_plan = AdminPlan.objects.get_or_create(
            name='adminAnnual',
            defaults={'description': 'Annual', 'stripe_price_id': 'price2', 'price_cents': 25000}
        )[0]

        now = timezone.now()

        # Admin Trial
        self.trial_user = CustomUser.objects.create_user(
            email="trial@test.com", username="trial@test.com", password="pass",
            role="admin", subscription_status="admin_trial", is_active=True
        )
        AdminProfile.objects.create(user=self.trial_user, trial_start_date=now)

        # Admin Monthly
        self.monthly_user = CustomUser.objects.create_user(
            email="monthly@test.com", username="monthly@test.com", password="pass",
            role="admin", subscription_status="admin_monthly", is_active=True
        )
        self.monthly_billing = now + timedelta(days=30)
        AdminProfile.objects.create(
            user=self.monthly_user,
            subscription_started_at=now,
            next_billing_date=self.monthly_billing
        )

        # Admin Annual
        self.annual_user = CustomUser.objects.create_user(
            email="annual@test.com", username="annual@test.com", password="pass",
            role="admin", subscription_status="admin_annual", is_active=True
        )
        self.annual_billing = now + timedelta(days=365)
        AdminProfile.objects.create(
            user=self.annual_user,
            subscription_started_at=now,
            next_billing_date=self.annual_billing
        )

        # Admin Inactive
        self.inactive_user = CustomUser.objects.create_user(
            email="inactive@test.com", username="inactive@test.com", password="pass",
            role="admin", subscription_status="admin_inactive", is_active=True
        )
        AdminProfile.objects.create(user=self.inactive_user)

        # Login as SuperAdmin
        login = self.client.post(reverse("superadmin_login"), data={
            "username": "superadmin@test.com",
            "password": "superpass123"
        }, content_type="application/json")
        self.token = login.json().get("access")
        self.auth_headers = {"HTTP_AUTHORIZATION": f"Bearer {self.token}"}

    def test_amounts_and_billing_dates_render_properly(self):
        response = self.client.get(reverse("superadmin-dashboard"), **self.auth_headers)
        self.assertEqual(response.status_code, 200)

        admins = response.json().get("admins", [])
        self.assertEqual(len(admins), 4)

        trial_admin = next(a for a in admins if a["email"] == "trial@test.com")
        self.assertEqual(trial_admin["price"], self.monthly_plan.price_dollars())
        self.assertEqual(trial_admin["next_billing_date"], (timezone.now() + timedelta(days=14)).strftime('%Y-%m-%d'))

        monthly_admin = next(a for a in admins if a["email"] == "monthly@test.com")
        self.assertEqual(monthly_admin["price"], self.monthly_plan.price_dollars())
        self.assertEqual(monthly_admin["next_billing_date"], self.monthly_billing.strftime('%Y-%m-%d'))

        annual_admin = next(a for a in admins if a["email"] == "annual@test.com")
        self.assertEqual(annual_admin["price"], self.annual_plan.price_dollars())
        self.assertEqual(annual_admin["next_billing_date"], self.annual_billing.strftime('%Y-%m-%d'))

        inactive_admin = next(a for a in admins if a["email"] == "inactive@test.com")
        self.assertEqual(inactive_admin["price"], "")
        self.assertEqual(inactive_admin["next_billing_date"], "")

        print("✅ SuperAdmin dashboard displays correct amounts and billing dates.")
