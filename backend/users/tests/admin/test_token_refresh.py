from rest_framework.test import APITestCase
from django.urls import reverse
from users.models import CustomUser
from adminplans.models import AdminProfile
from django.utils import timezone

class AdminTokenRefreshTests(APITestCase):
    def setUp(self):
        self.email = "tokenadmin@test.com"
        self.password = "securepass123"

        self.admin = CustomUser.objects.create_user(
            username=self.email,
            email=self.email,
            password=self.password,
            role="admin",
            is_staff=True,
            subscription_status="admin_trial"
        )

        AdminProfile.objects.create(
            user=self.admin,
            trial_start_date=timezone.now(),
            admin_stripe_customer_id="cus_test_456"
        )

    def test_admin_token_refresh_and_access_dashboard(self):
        # Step 1: Login to get refresh token
        login_response = self.client.post(
            reverse("admin-login"),
            data={"email": self.email, "password": self.password},
            content_type="application/json"
        )
        self.assertEqual(login_response.status_code, 200)

        refresh_token = login_response.json().get("refresh")
        self.assertIsNotNone(refresh_token)

        # Step 2: Use refresh token to get a new access token
        refresh_response = self.client.post(
            "/api/test-admin/token/refresh/",
            data={"refresh": refresh_token},
            content_type="application/json"
        )
        self.assertEqual(refresh_response.status_code, 200)

        new_access_token = refresh_response.json().get("access")
        self.assertIsNotNone(new_access_token)

        # Step 3: Access protected dashboard using new access token
        dashboard_response = self.client.get(
            reverse("admin-dashboard"),
            HTTP_AUTHORIZATION=f"Bearer {new_access_token}"
        )

        self.assertEqual(dashboard_response.status_code, 200)
        self.assertIn("trial_active", dashboard_response.data)
