from tests.base.base_admin_test import BaseAdminTest
from django.urls import reverse
from users.models.custom_user import CustomUser
from users.models.admin.admin_password_reset_token import AdminPasswordResetToken
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from rest_framework import status

class AdminResetPasswordSuccessTest(BaseAdminTest):
    def setUp(self):
        super().setUp()
        self.admin_email = "resetadmin@example.com"
        self.original_password = "oldPass123"
        self.new_password = "newStrongPass456"

        self.user = CustomUser.objects.create_user(
            username=self.admin_email,
            email=self.admin_email,
            password=self.original_password,
            role="admin",
            is_active=True
        )

        self.token = default_token_generator.make_token(self.user)
        self.uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        AdminPasswordResetToken.objects.create(user=self.user, token=self.token)

    def test_reset_password_successfully(self):
        response = self.client.post(
            reverse("admin_reset_password_confirm"),
            data={
                "uid": self.uid,
                "token": self.token,
                "new_password": self.new_password
            },
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)

        # Token should be deleted
        self.assertFalse(AdminPasswordResetToken.objects.filter(user=self.user).exists())

        # Password should be updated (old one fails, new one passes)
        self.user.refresh_from_db()
        self.assertFalse(self.user.check_password(self.original_password))
        self.assertTrue(self.user.check_password(self.new_password))


        print("✅ Admin password successfully reset and token cleared.")
