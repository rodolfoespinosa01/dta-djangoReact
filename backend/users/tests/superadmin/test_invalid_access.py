from rest_framework.test import APITestCase
from django.urls import reverse
from users.models import CustomUser

class SuperAdminRouteProtectionTests(APITestCase):
    def setUp(self):
        self.admin_email = "notallowed@test.com"
        self.password = "badpass123"

        self.admin = CustomUser.objects.create_user(
            username=self.admin_email,
            email=self.admin_email,
            password=self.password,
            role='admin',
            is_staff=True,
            subscription_status='admin_trial'
        )

    def test_admin_cannot_access_superadmin_dashboard(self):
        # 🚫 Try logging into superadmin endpoint with admin credentials
        login_response = self.client.post(
            reverse('superadmin-login'),
            data={'username': self.admin_email, 'password': self.password},
            content_type='application/json'
        )

        # ✅ Login must fail
        self.assertEqual(login_response.status_code, 401)
        self.assertIn("error", login_response.data)

