# backend/tests/admin/registration/test_admin_token_cannot_be_reused.py

from tests.base.base_admin_test import BaseAdminTest
from django.urls import reverse
from adminplans.models import PendingAdminSignup, AdminPlan
from users.models import CustomUser
from rest_framework import status
from unittest.mock import patch, MagicMock

class AdminTokenReuseTest(BaseAdminTest):
    def setUp(self):
        super().setUp()

        # 🧪 Ensure AdminPlan exists
        AdminPlan.objects.get_or_create(
            name='adminMonthly',
            defaults={
                'description': 'Monthly Admin Plan',
                'stripe_price_id': 'price_test_monthly',
                'price_cents': 2999,
            }
        )

        # 🧪 Create PendingAdminSignup manually
        PendingAdminSignup.objects.create(
            email="tokenreuse@test.com",
            session_id="cs_test_123",
            token="testtoken123",
            plan="adminMonthly",
            subscription_id="sub_test456"
        )

    @patch("stripe.checkout.Session.retrieve")
    def test_token_can_only_be_used_once(self, mock_stripe_session):
        mock_session = MagicMock()
        mock_session.mode = 'subscription'
        mock_session.customer = 'cus_test123'
        mock_session.customer_email = 'tokenreuse@test.com'
        mock_session.metadata = {'plan_name': 'adminMonthly'}

        mock_session.get.side_effect = lambda key, default=None: {
            "customer": "cus_test123",
            "customer_email": "tokenreuse@test.com",
            "metadata": {"plan_name": "adminMonthly"}
        }.get(key, default)

        mock_stripe_session.return_value = mock_session

        # ✅ First registration attempt
        first_response = self.client.post(
            reverse("register_admin"),
            data={
                "email": "tokenreuse@test.com",
                "password": "mypassword123",
                "token": "testtoken123"
            },
            content_type="application/json"
        )

        print("🔍 First Response JSON:", first_response.json())
        print("🔍 First Response Status:", first_response.status_code)
        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)

        # ❌ Second attempt using same token
        second_response = self.client.post(
            reverse("register_admin"),
            data={
                "email": "tokenreuse2@test.com",
                "password": "mypassword123",
                "token": "testtoken123"
            },
            content_type="application/json"
        )

        self.assertEqual(second_response.status_code, 404)
