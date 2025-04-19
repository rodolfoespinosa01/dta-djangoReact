from tests.base.base_admin_test import BaseAdminTest
from django.urls import reverse
from users.models import CustomUser

class SuperAdminRouteProtectionTests(BaseAdminTest):
    def setUp(self):
        self.admin_username = "admin_regular"
        self.admin_password = "badpass123"

        self.admin = CustomUser.objects.create_user(
            username=self.admin_username,
            email="admin@test.com",
            password=self.admin_password,
            role="admin",
            is_staff=True  # not a superuser!
        )

    def test_admin_cannot_access_superadmin_login(self):
        print("🚫 Test: Admin cannot login through SuperAdmin route")

        login_response = self.client.post(
            reverse('superadmin-login'),
            data={
                'username': self.admin_username,
                'password': self.admin_password
            },
            content_type='application/json'
        )

        self.assertEqual(login_response.status_code, 400)
        self.assertIn("Not authorized", str(login_response.data.get("non_field_errors", "")))