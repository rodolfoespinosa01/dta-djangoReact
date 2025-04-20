from django.utils import timezone
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.test import APIClient
from unittest.mock import patch
from users.models import CustomUser
from adminplans.models import AdminProfile, AdminPlan, AdminAccountHistory
from tests.base.base_admin_test import BaseAdminTest
from datetime import datetime, timezone as dt_timezone


class AdminCancelPaidSubscriptionTest(BaseAdminTest):
    def setUp(self):
        super().setUp()

        # Get pre-seeded adminMonthly plan
        self.plan = AdminPlan.objects.get(name="adminMonthly")

        # Create a paid admin user
        self.admin = CustomUser.objects.create_user(
            username="paidadmin@test.com",
            email="paidadmin@test.com",
            password="securepass123",
            role="admin",
            is_staff=True,
            subscription_status="admin_monthly"
        )

        # Create admin profile
        self.profile = AdminProfile.objects.create(
            user=self.admin,
            subscription_started_at=timezone.now(),
            next_billing_date=timezone.now() + timezone.timedelta(days=30),
            admin_stripe_subscription_id="sub_123456789",
            admin_stripe_customer_id="cus_123456789"
        )

        # Authenticate using DRF APIClient
        self.client = APIClient()
        refresh = RefreshToken.for_user(self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')

    @patch("stripe.Subscription.modify")
    @patch("stripe.Subscription.retrieve")
    def test_cancel_paid_plan_updates_profile_and_history(self, mock_retrieve, mock_modify):
        # Simulate Stripe returning current_period_end timestamp
        future_timestamp = int((timezone.now() + timezone.timedelta(days=30)).timestamp())
        mock_retrieve.return_value = {"current_period_end": future_timestamp}
        mock_modify.return_value = {"id": "sub_123456789", "cancel_at_period_end": True}

        # Hit cancel endpoint
        response = self.client.post("/api/users/admin/cancel-auto-renew/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.profile.refresh_from_db()
        self.assertTrue(self.profile.is_canceled)
        self.assertTrue(self.profile.auto_renew_cancelled)
        self.assertIsNone(self.profile.next_billing_date)

        # Confirm subscription_end_date matches Stripe value
        expected_end = datetime.fromtimestamp(future_timestamp, tz=dt_timezone.utc)
        self.assertEqual(self.profile.subscription_end_date, expected_end)

        # Check history was created
        history = AdminAccountHistory.objects.filter(admin=self.admin).last()
        self.assertIsNotNone(history)
        self.assertEqual(history.plan_name, "admin_monthly")
        self.assertTrue(history.was_canceled)
        self.assertEqual(history.end_date, expected_end)
