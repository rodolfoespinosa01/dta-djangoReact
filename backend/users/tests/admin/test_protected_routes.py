from rest_framework.test import APITestCase
from django.urls import reverse

class AdminProtectedRouteTest(APITestCase):
    def test_admin_dashboard_requires_auth(self):
        print("🔒 Test: Admin cannot access dashboard if not logged in")

        response = self.client.get(reverse('admin-dashboard'))

        self.assertEqual(response.status_code, 401)
