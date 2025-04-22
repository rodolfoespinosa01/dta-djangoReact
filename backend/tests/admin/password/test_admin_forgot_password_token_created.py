from tests.base.base_admin_test import BaseAdminTest
from django.urls import reverse
from users.models.custom_user import CustomUser
from users.models.admin.admin_password_reset_token import AdminPasswordResetToken
from rest_framework import status

class AdminForgotPasswordTokenTest(BaseAdminTest):
    def setUp(self):
        super().setUp()
        self.admin_email = "adminforgot@example.com"
        self.admin_user = CustomUser.objects.create_user(
            username=self.admin_email,
            email=self.admin_email,
            password="initialPass123",
            role="admin",
            is_active=True
        )

    def test_forgot_password_creates_token_and_prints_email(self):
        response = self.client.post(
            reverse("admin_forgot_password"),
            data={"email": self.admin_email},
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Password reset link sent", response.json().get("detail", ""))

        token_entry = AdminPasswordResetToken.objects.filter(user=self.admin_user).first()
        self.assertIsNotNone(token_entry)
