from tests.base.base_admin_test import BaseAdminTest
from django.urls import reverse
from core.models import CustomUser
from users.admin_area.models import AdminPasswordResetToken
from unittest.mock import patch
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

    @patch("builtins.print")
    def test_forgot_password_creates_token_and_prints_email(self, mock_print):
        response = self.client.post(
            reverse("admin_forgot_password"),
            data={"email": self.admin_email},
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Password reset link sent", response.json().get("detail", ""))

        # Token was created
        token_entry = AdminPasswordResetToken.objects.filter(user=self.admin_user).first()
        self.assertIsNotNone(token_entry)

        # Email (print) was triggered
        printed_output = "\n".join([str(call.args[0]) for call in mock_print.call_args_list])
        self.assertIn("📩 Admin Password Reset Email", printed_output)
        self.assertIn(self.admin_email, printed_output)
        self.assertIn("reset your password", printed_output.lower())

        print("✅ Forgot password token created and reset link printed successfully.")
