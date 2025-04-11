from rest_framework.test import APITestCase
from django.urls import reverse
from users.models import CustomUser

class SuperAdminDashboardAccessTest(APITestCase):
    def test_superadmin_can_login_and_access_dashboard(self):
        print("🛡️  Test: SuperAdmin can login and access dashboard")

        # Step 1: Create SuperAdmin
        user = CustomUser.objects.create_superuser(
            username="dta_user",
            email="",
            password="dta6914"
        )

        # Step 2: Login
        login_response = self.client.post(
            reverse('superadmin-login'),
            data={'username': "dta_user", 'password': "dta6914"},
            content_type='application/json'
        )
        self.assertEqual(login_response.status_code, 200)
        token = login_response.json().get("access")
        self.assertIsNotNone(token)

        # Step 3: Hit SuperAdmin dashboard
        dashboard_response = self.client.get(
            reverse('superadmin-dashboard'),
            HTTP_AUTHORIZATION=f'Bearer {token}'
        )

        self.assertEqual(dashboard_response.status_code, 200)
        self.assertIn("trial_admins", dashboard_response.data)
        self.assertIn("monthly_admins", dashboard_response.data)
        self.assertIn("annual_admins", dashboard_response.data)
        self.assertIn("total_revenue", dashboard_response.data)
        self.assertIn("projected_monthly_income", dashboard_response.data)
