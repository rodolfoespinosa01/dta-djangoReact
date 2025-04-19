from tests.base.base_admin_test import BaseAdminTest
from django.urls import reverse
from rest_framework import status

class AdminInvalidTokenTest(BaseAdminTest):
    def test_admin_registration_with_invalid_token(self):
        print("❌ Test: Admin registration with invalid token")

        response = self.client.post(
            reverse("register-admin"),
            data={
                "email": "fakeadmin@test.com",
                "password": "securepass123",
                "token": "invalidtoken999"
            },
            content_type="application/json"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("error", response.json())
        self.assertEqual(response.json()["error"], "Invalid or expired token")
