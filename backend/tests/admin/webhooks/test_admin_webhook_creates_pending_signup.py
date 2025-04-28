# backend/tests/admin/webhooks/test_admin_webhook_creates_pending_signup.py

from tests.base.base_admin_test import BaseAdminTest
from django.urls import reverse
from adminplans.models import AdminPendingSignup
import stripe
import json
from unittest.mock import patch

class AdminStripeWebhookTest(BaseAdminTest):
    @patch("stripe.Webhook.construct_event")
    def test_webhook_creates_pending_signup(self, mock_construct_event):
        print("📩 Test: Webhook creates AdminPendingSignup")

        mock_event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_123",
                    "customer_email": "webhooktest@example.com",
                    "subscription": "sub_test456",
                    "metadata": {
                        "plan_name": "adminMonthly"
                    }
                }
            }
        }
        mock_construct_event.return_value = mock_event

        response = self.client.post(
            reverse("admin_stripe_webhook"),
            data=json.dumps(mock_event),
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="test_signature"
        )

        self.assertEqual(response.status_code, 200)
        pending = AdminPendingSignup.objects.get(email="webhooktest@example.com")
        self.assertEqual(pending.plan, "adminMonthly")
        self.assertEqual(pending.subscription_id, "sub_test456")
