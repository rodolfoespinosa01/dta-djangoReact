from rest_framework.test import APITestCase
from django.urls import reverse
from users.models import CustomUser

class AdminLoginValidTest(APITestCase):
    def setUp(self):
        self.email = "validadmin@test.com"
        self.password = "strongpass123"

        self.admin = CustomUser.objects.create_user(
            username=self.email,  # ✅ TokenObtainPairView uses this
            email=self.email,
            password=self.password,
            role='admin',
            is_staff=True,
            subscription_status='admin_trial'
        )

    def test_admin_login_valid_credentials(self):
        print("✅ Test: Admin login with valid credentials")

        response = self.client.post(
            reverse('admin-login'),
            data={'username': self.email, 'password': self.password},
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.json())
