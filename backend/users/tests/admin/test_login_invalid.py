from rest_framework.test import APITestCase
from django.urls import reverse
from users.models import CustomUser

class AdminLoginInvalidTest(APITestCase):
    def setUp(self):
        self.email = "invalidadmin@test.com"
        self.password = "validpass123"

        self.admin = CustomUser.objects.create_user(
            username=self.email,
            email=self.email,
            password=self.password,
            role='admin',
            is_staff=True,
            subscription_status='admin_trial'
        )

    def test_admin_login_invalid_credentials(self):
        print("❌ Test: Admin login with invalid credentials")

        response = self.client.post(
            reverse('admin-login'),
            data={'email': self.email, 'password': 'wrongpassword'},
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 401)
        self.assertIn("error", response.json())
