# backend/users/tests/test_auth.py

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

class AdminAuthTests(TestCase):
    def setUp(self):
        self.email = "admin@test.com"
        self.password = "securepassword"
        self.user = User.objects.create_user(
            username=self.email,
            email=self.email,
            password=self.password,
            role='admin'
        )

    def test_admin_login_valid_credentials(self):
        """
        ✅ Test: Admin login with valid credentials
        """
        response = self.client.post(reverse('admin-login'), {
            'email': self.email,
            'password': self.password
        }, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.json())
        self.assertIn('refresh', response.json())

    def test_admin_login_invalid_credentials(self):
        """
        ❌ Test: Admin login with invalid credentials
        """
        response = self.client.post(reverse('admin-login'), {
            'email': self.email,
            'password': 'wrongpassword'
        }, content_type='application/json')

        self.assertEqual(response.status_code, 401)
        self.assertIn('error', response.json())
