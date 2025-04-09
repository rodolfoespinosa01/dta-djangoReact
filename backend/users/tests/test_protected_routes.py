# backend/users/tests/test_protected_routes.py

from django.test import TestCase
from django.urls import reverse

class AdminProtectedRoutesTests(TestCase):
    def test_admin_dashboard_requires_auth(self):
        """
        🔒 Test: Admin cannot access dashboard if not logged in
        """
        response = self.client.get("/api/users/admindashboard/")
        self.assertEqual(response.status_code, 401)
        self.assertIn('detail', response.json())
        self.assertEqual(response.json()['detail'], 'Authentication credentials were not provided.')
