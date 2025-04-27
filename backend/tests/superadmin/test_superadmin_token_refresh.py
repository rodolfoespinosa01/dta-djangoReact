from tests.base.base_admin_test import BaseAdminTest
from django.urls import reverse
from users.models import CustomUser

class SuperAdminTokenRefreshTests(BaseAdminTest):
    def setUp(self):
        self.username = "superadmin_refresh"
        self.email = "superadmin_refresh@test.com"
        self.password = "dta6914"

        # ✅ Create superuser with username + email
        self.superadmin = CustomUser.objects.create_superuser(
            username=self.username,
            email=self.email,
            password=self.password
        )

    def test_superadmin_token_refresh_and_dashboard_access(self):
        print("🔄 Test: SuperAdmin token refresh and dashboard access")

        # ✅ Step 1: Login with username (not email)
        login_response = self.client.post(
            reverse("superadmin_login"),
            data={"username": self.username, "password": self.password},
            content_type="application/json"
        )
        self.assertEqual(login_response.status_code, 200)

        refresh_token = login_response.data.get("refresh")
        self.assertIsNotNone(refresh_token)

        # ✅ Step 2: Refresh token
        refresh_response = self.client.post(
            reverse("test-superadmin-token-refresh"),
            data={"refresh": refresh_token},
            content_type="application/json"
        )
        self.assertEqual(refresh_response.status_code, 200)

        new_access_token = refresh_response.data.get("access")
        self.assertIsNotNone(new_access_token)

        # ✅ Step 3: Access SuperAdmin dashboard with new access token
        dashboard_response = self.client.get(
            reverse("superadmin-dashboard"),
            HTTP_AUTHORIZATION=f"Bearer {new_access_token}"
        )
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertIn("admins", dashboard_response.data)
