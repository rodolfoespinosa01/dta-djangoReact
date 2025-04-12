from rest_framework.test import APITestCase
from django.urls import reverse
from users.models import CustomUser

class SuperAdminTokenRefreshTests(APITestCase):
    def setUp(self):
        self.username = "superadmin_refresh"
        self.password = "dta6914"

        self.superadmin = CustomUser.objects.create_superuser(
            username=self.username,
            email="",
            password=self.password
        )

    def test_superadmin_token_refresh_and_dashboard_access(self):
        # Step 1: Login to get refresh token
        login_response = self.client.post(
            reverse("superadmin-login"),
            data={"username": self.username, "password": self.password},
            content_type="application/json"
        )
        self.assertEqual(login_response.status_code, 200)

        refresh_token = login_response.json().get("refresh")
        self.assertIsNotNone(refresh_token)

        # Step 2: Refresh the token via test-only endpoint
        refresh_response = self.client.post(
            "/api/test-superadmin/token/refresh/",
            data={"refresh": refresh_token},
            content_type="application/json"
        )
        self.assertEqual(refresh_response.status_code, 200)

        new_access_token = refresh_response.json().get("access")
        self.assertIsNotNone(new_access_token)

        # Step 3: Use new token to access protected superadmin dashboard
        dashboard_response = self.client.get(
            reverse("superadmin-dashboard"),
            HTTP_AUTHORIZATION=f"Bearer {new_access_token}"
        )
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertIn("trial_admins", dashboard_response.data)
