from tests.base.base_admin_test import BaseAdminTest
from django.urls import reverse
from users.models import CustomUser

class SuperAdminDashboardAccessTest(BaseAdminTest):
    def test_superadmin_can_login_and_access_dashboard(self):
        print("🛡️  Test: SuperAdmin can login and access dashboard")

        # Step 1: Create SuperAdmin with valid email
        user = CustomUser.objects.create_superuser(
            username="dta_user",
            email="superadmin@test.com",
            password="dta6914"
        )

        # Step 2: Login with correct field
        login_response = self.client.post(
            reverse('superadmin_login'),
            data={'username': "dta_user", 'password': "dta6914"},
            content_type='application/json'
        )

        self.assertEqual(login_response.status_code, 200)

        token = login_response.data.get("access")
        self.assertIsNotNone(token)

        # Step 3: Access dashboard with token
        dashboard_response = self.client.get(
            reverse("superadmin_dashboard"),
            HTTP_AUTHORIZATION=f'Bearer {token}'
        )

        self.assertEqual(dashboard_response.status_code, 200)
        self.assertIn("admins", dashboard_response.data)
