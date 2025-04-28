from tests.base.base_admin_test import BaseAdminTest
from django.urls import reverse
from adminplans.models import AdminPendingSignup, AdminPlan, AdminProfile
from users.models.custom_user import CustomUser
from unittest.mock import patch, MagicMock
from rest_framework import status
import stripe
from datetime import timedelta
from django.utils import timezone

class AdminAnnualRegistrationTest(BaseAdminTest):
    def setUp(self):
        super().setUp()

        # Ensure annual AdminPlan exists
        AdminPlan.objects.get_or_create(
            name='adminAnnual',
            defaults={
                'description': 'Annual Admin Plan',
                'stripe_price_id': 'price_test_annual',
                'price_cents': 29999,
            }
        )

        # Simulate webhook created token
        AdminPendingSignup.objects.create(
            email="annualtest@example.com",
            session_id="cs_test_annual",
            token="annualtoken123",
            plan="adminAnnual",
            subscription_id="sub_annual_789"
        )

    @patch("stripe.checkout.Session.retrieve")
    def test_paid_annual_plan_registers_correctly(self, mock_stripe_session):
        mock_session = MagicMock()
        mock_session.mode = 'subscription'
        mock_session.customer = 'cus_annual_789'
        mock_session.customer_email = 'annualtest@example.com'
        mock_session.get.side_effect = lambda key, default=None: {
            "customer": "cus_annual_789",
            "customer_email": "annualtest@example.com",
            "metadata": {"plan_name": "adminAnnual"}
        }.get(key, default)

        mock_stripe_session.return_value = mock_session

        response = self.client.post(
            reverse("admin_register"),
            data={
                "email": "annualtest@example.com",
                "password": "strongpass123",
                "token": "annualtoken123"
            },
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 201)
        self.assertIn("access", response.json())

        user = CustomUser.objects.get(email="annualtest@example.com")
        self.assertEqual(user.subscription_status, "admin_annual")

        profile = AdminProfile.objects.get(user=user)
        self.assertEqual(profile.admin_stripe_customer_id, "cus_annual_789")
        self.assertEqual(profile.admin_stripe_subscription_id, "sub_annual_789")
        self.assertIsNotNone(profile.subscription_started_at)
        self.assertIsNotNone(profile.next_billing_date)

        # Check next billing date is roughly one year from now
        now = timezone.now()
        expected_next = profile.subscription_started_at + timedelta(days=365)
        delta = abs((profile.next_billing_date - expected_next).days)
        self.assertLessEqual(delta, 1)

        print("✅ Annual admin registration successful and billing info stored.")
