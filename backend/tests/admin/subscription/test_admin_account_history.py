import stripe
from datetime import timedelta
from django.utils import timezone
from django.test import override_settings
from rest_framework.test import APITestCase
from users.models import CustomUser
from adminplans.models import AdminPlan, AdminProfile, AdminAccountHistory
from unittest.mock import patch

@override_settings(STRIPE_SECRET_KEY='sk_test_dummy')
class AdminAccountHistoryFlowTest(APITestCase):
    def setUp(self):
        self.plan = AdminPlan.objects.get(name='adminMonthly')
        self.admin = CustomUser.objects.create_user(
            username='historyflowadmin',
            email='historyflowadmin@test.com',
            password='securepass123',
            role='admin',
            subscription_status='admin_monthly'
        )

        self.patcher = patch('stripe.Webhook.construct_event', return_value={
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "metadata": {
                        "reactivated_email": self.admin.email,
                        "plan_name": self.plan.name
                    },
                    "subscription": "sub_reactivation_history"
                }
            }
        })
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_account_history_for_signup_cancel_reactivation(self):
        now = timezone.now()

        # ✅ Create AdminProfile (signup)
        profile = AdminProfile.objects.create(
            user=self.admin,
            subscription_started_at=now,
            next_billing_date=now + timedelta(days=30),
            admin_stripe_customer_id="cus_history_1",
            admin_stripe_subscription_id="sub_history_1"
        )

        AdminAccountHistory.objects.create(
            admin=self.admin,
            plan_name='admin_monthly',
            subscription_id='sub_history_1',
            start_date=now,
            end_date=None,
            was_canceled=False
        )

        # ✅ Cancel account
        profile.is_canceled = True
        profile.canceled_at = now + timedelta(days=10)
        profile.subscription_end_date = now + timedelta(days=30)
        profile.next_billing_date = None
        profile.save()

        AdminAccountHistory.objects.create(
            admin=self.admin,
            plan_name='admin_monthly',
            subscription_id='sub_history_1',
            start_date=now,
            end_date=now + timedelta(days=30),
            was_canceled=True
        )

        # ✅ Simulate reactivation webhook
        stripe.Subscription.retrieve = lambda sub_id: {
            "items": {
                "data": [{
                    "current_period_end": int((timezone.now() + timedelta(days=30)).timestamp())
                }]
            }
        }

        from adminplans.views.admin_stripe_reactivation_webhook import admin_stripe_reactivation_webhook
        from rest_framework.test import APIRequestFactory
        import json

        payload = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "metadata": {
                        "reactivated_email": self.admin.email,
                        "plan_name": self.plan.name
                    },
                    "subscription": "sub_reactivation_history"
                }
            }
        }

        factory = APIRequestFactory()
        request = factory.post(
            "/api/adminplans/admin_stripe_reactivation_webhook/",
            data=json.dumps(payload),
            content_type='application/json'
        )
        request.META['HTTP_STRIPE_SIGNATURE'] = 'mocked'
        response = admin_stripe_reactivation_webhook(request)
        self.assertEqual(response.status_code, 200)

        # ✅ Confirm all 3 history entries exist
        history = AdminAccountHistory.objects.filter(admin=self.admin)
        self.assertEqual(history.count(), 3)

        labels = [
            ('signup', False, None),
            ('cancel', True, now + timedelta(days=30)),
            ('reactivate', False, None)
        ]

        for index, (label, canceled, end) in enumerate(labels):
            entry = history[index]
            self.assertEqual(entry.was_canceled, canceled)
            if end:
                self.assertEqual(entry.end_date.date(), end.date())
