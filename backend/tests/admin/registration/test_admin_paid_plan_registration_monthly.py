# backend/tests/admin/registration/test_admin_paid_plan_registration_monthly.py

from tests.base.base_admin_test import BaseAdminTest
from django.urls import reverse
from adminplans.models import PendingAdminSignup, AdminPlan, AdminProfile
from users.models import CustomUser
from unittest.mock import patch, MagicMock
from rest_framework import status
import stripe

class AdminMonthlyRegistrationTest(BaseAdminTest):
    def setUp(self):
        super().setUp()

        # Ensure monthly AdminPlan exists
        AdminPlan.objects.get_or_create(
            name='adminMonthly',
            defaults={
                'description': 'Monthly Admin Plan',
                'stripe_price_id': 'price_test_monthly',
                'price_cents': 2999,
            }
        )

        # Simulate webhook created token
        PendingAdminSignup.objects.create(
            email="monthlytest@example.com",
            session_id="cs_test_monthly",
            token="monthlytoken123",
            plan="adminMonthly",
            subscription_id="sub_monthly_789"
        )

    @patch("stripe.checkout.Session.retrieve")
    def test_paid_monthly_plan_registers_correctly(self, mock_stripe_session):
        mock_session = MagicMock()
        mock_session.mode = 'subscription'
        mock_session.customer = 'cus_monthly_789'
        mock_session.customer_email = 'monthlytest@example.com'
        mock_session.get.side_effect = lambda key, default=None: {
            "customer": "cus_monthly_789",
            "customer_email": "monthlytest@example.com",
            "metadata": {"plan_name": "adminMonthly"}
        }.get(key, default)

        mock_stripe_session.return_value = mock_session

        response = self.client.post(
            reverse("register-admin"),
            data={
                "email": "monthlytest@example.com",
                "password": "strongpass123",
                "token": "monthlytoken123"
            },
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 201)
        self.assertIn("access", response.json())

        user = CustomUser.objects.get(email="monthlytest@example.com")
        self.assertEqual(user.subscription_status, "admin_monthly")

        profile = AdminProfile.objects.get(user=user)
        self.assertEqual(profile.admin_stripe_customer_id, "cus_monthly_789")
        self.assertEqual(profile.admin_stripe_subscription_id, "sub_monthly_789")
        self.assertIsNotNone(profile.subscription_started_at)

        print("✅ Monthly admin registration successful and billing info stored.")
