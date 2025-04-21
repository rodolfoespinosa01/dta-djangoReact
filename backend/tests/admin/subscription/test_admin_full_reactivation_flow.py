import stripe
from datetime import timedelta
from django.utils import timezone
from django.test import override_settings
from rest_framework.test import APITestCase
from users.models import CustomUser
from adminplans.models import AdminPlan, AdminProfile, AdminAccountHistory
from unittest.mock import patch

@override_settings(STRIPE_SECRET_KEY='sk_test_dummy')
class AdminFullReactivationFlowTest(APITestCase):
    def setUp(self):
        self.plan = AdminPlan.objects.get(name='adminMonthly')
        self.admin = CustomUser.objects.create_user(
            username='fullflowadmin',
            email='fullflowadmin@test.com',
            password='strongpassword123',
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
                    "subscription": "sub_reactivation_flow"
                }
            }
        })
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def simulate_reactivation(self, is_inactive):
        now = timezone.now()
        profile = AdminProfile.objects.create(
            user=self.admin,
            admin_stripe_customer_id='cus_test789',
            admin_stripe_subscription_id='sub_original',
            subscription_started_at=now - timedelta(days=30),
            next_billing_date=now + timedelta(days=10) if not is_inactive else None,
            subscription_end_date=None if not is_inactive else now - timedelta(days=1),
            is_canceled=True,
            auto_renew_cancelled=True,
            canceled_at=now - timedelta(days=1)
        )

        # Simulate Stripe reactivation webhook payload
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
                    "subscription": "sub_reactivation_flow"
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
        return response

    def test_reactivation_while_still_active(self):
        response = self.simulate_reactivation(is_inactive=False)
        self.assertEqual(response.status_code, 200)

        profile = AdminProfile.objects.get(user=self.admin)
        self.assertFalse(profile.is_canceled)
        self.assertIsNotNone(profile.next_billing_date)
        self.assertEqual(profile.admin_stripe_subscription_id, 'sub_reactivation_flow')

        history = AdminAccountHistory.objects.filter(admin=self.admin, subscription_id='sub_reactivation_flow')
        self.assertEqual(history.count(), 1)

    def test_reactivation_when_inactive(self):
        response = self.simulate_reactivation(is_inactive=True)
        self.assertEqual(response.status_code, 200)

        profile = AdminProfile.objects.get(user=self.admin)
        self.assertFalse(profile.is_canceled)
        self.assertIsNotNone(profile.next_billing_date)
        self.assertEqual(profile.admin_stripe_subscription_id, 'sub_reactivation_flow')

        history = AdminAccountHistory.objects.filter(admin=self.admin, subscription_id='sub_reactivation_flow')
        self.assertEqual(history.count(), 1)
