from tests.base.base_admin_test import BaseAdminTest
from django.urls import reverse
from core.models import CustomUser
from users.admin_area.models import AdminPasswordResetToken
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from rest_framework import status

class AdminOldPasswordFailsNewPassWorksTest(BaseAdminTest):
    def setUp(self):
        super().setUp()
        self.admin_email = "resetlogin@example.com"
        self.original_password = "originalPass123"
        self.new_password = "newPass456"

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

        # Perform password reset
        self.client.post(
            reverse("admin_reset_password_confirm"),
            data={
                "uid": self.uid,
                "token": self.token,
                "new_password": self.new_password
            },
            content_type="application/json"
        )

    def test_old_password_fails_new_password_works(self):
        # Try login with old password — should fail
        old_login = self.client.post(
            reverse("admin_login"),
            data={
                "username": self.admin_email,

                "password": self.original_password
            },
            content_type="application/json"
        )
        self.assertEqual(old_login.status_code, 401)

        # Try login with new password — should succeed
        new_login = self.client.post(
            reverse("admin_login"),
            data={
                "username": self.admin_email,

                "password": self.new_password
            },
            content_type="application/json"
        )
        self.assertEqual(new_login.status_code, 200)
        self.assertIn("access", new_login.json())

        print("✅ Old password blocked, new password login successful.")
