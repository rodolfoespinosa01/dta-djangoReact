# backend/users/tests/test_auth.py

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from users.models import CustomUser
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from adminplans.models import AdminProfile, AdminPlan

User = get_user_model()

class AdminAuthPersistenceTests(APITestCase):

    def setUp(self):
        self.admin_email = "persistadmin@test.com"
        self.password = "testpass123"

        self.admin = CustomUser.objects.create_user(
            username=self.admin_email,
            email=self.admin_email,
            password=self.password,
            role='admin',
            is_staff=True,
            subscription_status='admin_trial'
        )

        # Create valid AdminProfile for session persistence
        AdminProfile.objects.create(
            user=self.admin,
            trial_start_date=timezone.now(),
            subscription_started_at=None,
            admin_stripe_customer_id='cus_test123'
        )

    def test_admin_session_persists_via_token(self):
        # Step 1: Log in to get token
        login_response = self.client.post(
            reverse('admin-login'),
            data={'email': self.admin_email, 'password': self.password},
            content_type='application/json'
        )
        self.assertEqual(login_response.status_code, 200)
        token = login_response.json().get('access')
        self.assertIsNotNone(token)

        # Step 2: Access dashboard with token (simulate refresh)
        dashboard_response = self.client.get(
            reverse('admin-dashboard'),
            HTTP_AUTHORIZATION=f'Bearer {token}'
        )

        self.assertEqual(dashboard_response.status_code, 200)
        self.assertIn('trial_active', dashboard_response.data)

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
