from tests.base.base_admin_test import BaseAdminTest
from django.urls import reverse
from users.models.custom_user import CustomUser

class AdminLoginInvalidTest(BaseAdminTest):
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
            data={'username': self.email, 'password': 'wrongpassword'},  
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 401)

        # DRF's default TokenObtainPairView returns a 'detail' field on error
        self.assertIn("detail", response.data)
