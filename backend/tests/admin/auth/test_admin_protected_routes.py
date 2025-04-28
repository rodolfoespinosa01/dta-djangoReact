from tests.base.base_admin_test import BaseAdminTest
from django.urls import reverse

class AdminProtectedRouteTest(BaseAdminTest):
    def test_admin_dashboard_requires_auth(self):
        print("🔒 Test: Admin cannot access dashboard if not logged in")

        response = self.client.get(reverse('admin_dashboard'))

        self.assertEqual(response.status_code, 401)
