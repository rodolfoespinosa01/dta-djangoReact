from tests.base.base_admin_test import BaseAdminTest
from django.urls import reverse
from django.utils import timezone
from core.models import CustomUser
from users.admin_area.models import AdminProfile, AdminPlan

class SuperAdminDashboardGroupingTest(BaseAdminTest):
    def setUp(self):
        super().setUp()

        # Create SuperAdmin
        self.superadmin = CustomUser.objects.create_superuser(
            username="superadmin@test.com",
            email="superadmin@test.com",
            password="superpass123"
        )

        # Ensure required plans exist
        AdminPlan.objects.get_or_create(name='adminMonthly', defaults={'description': 'Monthly', 'stripe_price_id': 'price1', 'price_cents': 3000})
        AdminPlan.objects.get_or_create(name='adminAnnual', defaults={'description': 'Annual', 'stripe_price_id': 'price2', 'price_cents': 25000})

        now = timezone.now()

        # AdminTrial
        trial_user = CustomUser.objects.create_user(email="trial@test.com", username="trial@test.com", password="pass", role="admin", subscription_status="admin_trial", is_active=True)
        AdminProfile.objects.create(user=trial_user, trial_start_date=now)

        # AdminMonthly
        monthly_user = CustomUser.objects.create_user(email="monthly@test.com", username="monthly@test.com", password="pass", role="admin", subscription_status="admin_monthly", is_active=True)
        AdminProfile.objects.create(user=monthly_user, subscription_started_at=now, next_billing_date=now + timezone.timedelta(days=30))

        # AdminAnnual
        annual_user = CustomUser.objects.create_user(email="annual@test.com", username="annual@test.com", password="pass", role="admin", subscription_status="admin_annual", is_active=True)
        AdminProfile.objects.create(user=annual_user, subscription_started_at=now, next_billing_date=now + timezone.timedelta(days=365))

        # AdminInactive
        inactive_user = CustomUser.objects.create_user(email="inactive@test.com", username="inactive@test.com", password="pass", role="admin", subscription_status="admin_inactive", is_active=True)
        AdminProfile.objects.create(user=inactive_user)

        # Auth: login as superadmin
        login = self.client.post(reverse("superadmin_login"), data={"username": "superadmin@test.com", "password": "superpass123"}, content_type="application/json")
        self.token = login.json().get("access")
        self.auth_headers = {"HTTP_AUTHORIZATION": f"Bearer {self.token}"}

    def test_dashboard_returns_grouped_admins(self):
        response = self.client.get(reverse("superadmin_dashboard"), **self.auth_headers)
        self.assertEqual(response.status_code, 200)

        plans = {admin["plan"]: admin["email"] for admin in response.json()["admins"]}
        self.assertIn("admin_trial", plans)
        self.assertIn("admin_monthly", plans)
        self.assertIn("admin_annual", plans)
        self.assertIn("admin_inactive", plans)

        print("✅ SuperAdmin dashboard returns grouped admin plans correctly.")
