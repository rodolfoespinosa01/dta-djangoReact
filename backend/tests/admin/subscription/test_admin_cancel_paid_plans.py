from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import patch
from datetime import datetime, timezone as dt_timezone

from users.models import CustomUser
from adminplans.models import AdminProfile, AdminPlan, AdminAccountHistory
from tests.base.base_admin_test import BaseAdminTest


class AdminCancelPaidPlansTest(BaseAdminTest):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

    @patch("stripe.Subscription.modify")
    @patch("stripe.Subscription.retrieve")
    def test_cancel_all_paid_plans(self, mock_retrieve, mock_modify):
        # Loop through all active paid plans dynamically from DB
        paid_plans = AdminPlan.objects.exclude(name="adminTrial")

        for plan in paid_plans:
            with self.subTest(plan=plan.name):
                email = f"{plan.name.lower()}@test.com"
                user = CustomUser.objects.create_user(
                    username=email,
                    email=email,
                    password="securepass123",
                    role="admin",
                    is_staff=True,
                    subscription_status=plan.name.lower()
                )

                next_billing = timezone.now() + timezone.timedelta(days=30)
                profile = AdminProfile.objects.create(
                    user=user,
                    subscription_started_at=timezone.now(),
                    next_billing_date=next_billing,
                    admin_stripe_subscription_id="sub_test_123",
                    admin_stripe_customer_id="cus_test_123"
                )

                # Auth
                refresh = RefreshToken.for_user(user)
                self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')

                # Mock Stripe API
                future_timestamp = int(next_billing.timestamp())
                mock_retrieve.return_value = {"current_period_end": future_timestamp}
                mock_modify.return_value = {"id": "sub_test_123", "cancel_at_period_end": True}

                # Call endpoint
                response = self.client.post("/api/adminplans/admin_cancel_subscription/")
                self.assertEqual(response.status_code, status.HTTP_200_OK)

                profile.refresh_from_db()
                expected_end = datetime.fromtimestamp(future_timestamp, tz=dt_timezone.utc)

                # Assertions
                self.assertTrue(profile.is_canceled)
                self.assertTrue(profile.auto_renew_cancelled)
                self.assertIsNone(profile.next_billing_date)
                self.assertEqual(profile.subscription_end_date, expected_end)

                history = AdminAccountHistory.objects.filter(admin=user).last()
                self.assertIsNotNone(history)
                self.assertEqual(history.plan_name, user.subscription_status)
                self.assertTrue(history.was_canceled)
                self.assertEqual(history.end_date, expected_end)
