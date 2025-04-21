from datetime import timedelta, datetime, timezone as dt_timezone
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import patch

from users.models import CustomUser
from adminplans.models import AdminPlan, AdminProfile, AdminAccountHistory
from tests.base.base_admin_test import BaseAdminTest

class AdminCancelTrialSubscriptionTest(BaseAdminTest):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

    @patch("stripe.Subscription.modify")
    @patch("stripe.Subscription.retrieve")
    def test_cancel_all_admin_plans(self, mock_retrieve, mock_modify):
        plans = [
            ("adminTrial", "admin_trial", 14),
            ("adminMonthly", "admin_monthly", 30),
            ("adminQuarterly", "admin_quarterly", 90),
            ("adminAnnual", "admin_annual", 365),
        ]

        for plan_key, sub_status, duration_days in plans:
            with self.subTest(plan=plan_key):
                now = timezone.now()
                future_end = now + timedelta(days=duration_days)

                # Use adminMonthly plan object for trial too (as in production)
                plan_name = "adminMonthly" if plan_key == "adminTrial" else plan_key
                plan = AdminPlan.objects.get(name=plan_name)

                email = f"{sub_status}@test.com"
                user = CustomUser.objects.create_user(
                    username=email,
                    email=email,
                    password="securepass123",
                    role="admin",
                    is_staff=True,
                    subscription_status=sub_status
                )

                profile = AdminProfile.objects.create(
                    user=user,
                    subscription_started_at=now,
                    next_billing_date=future_end,
                    admin_stripe_subscription_id="sub_test_123",
                    admin_stripe_customer_id="cus_test_123"
                )

                refresh = RefreshToken.for_user(user)
                self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')

                # ✅ Patch the Stripe subscription response
                mock_modify.return_value = {"id": "sub_test_123", "cancel_at_period_end": True}
                mock_retrieve.return_value = {"current_period_end": int(future_end.timestamp())}

                # 🚀 Hit the cancel endpoint
                response = self.client.post("/api/adminplans/admin_cancel_subscription/")
                self.assertEqual(response.status_code, status.HTTP_200_OK)

                profile.refresh_from_db()
                expected_end = datetime.fromtimestamp(int(future_end.timestamp()), tz=dt_timezone.utc)

                self.assertTrue(profile.is_canceled)
                self.assertIsNone(profile.next_billing_date)
                self.assertEqual(profile.subscription_end_date.date(), expected_end.date())

                # ✅ Check history record
                history = AdminAccountHistory.objects.filter(admin=user).last()
                self.assertIsNotNone(history)
                self.assertEqual(history.plan_name, sub_status)
                self.assertTrue(history.was_canceled)
                self.assertEqual(history.end_date.date(), expected_end.date())
