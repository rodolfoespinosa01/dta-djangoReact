from django.db import models  # 👉 provides access to django model classes and fields
from django.conf import settings
from django.contrib.auth import get_user_model  # 👉 allows referencing the custom user model dynamically

User = get_user_model()  # 👉 gets the project's configured custom user model


class AccountHistory(models.Model):  # 👉 stores a history log of user account events (signup, cancel, etc.)

    EVENT_CHOICES = [
    # 🟢 New Subscriptions
    ('trial_monthly_start', 'Trial - Monthly Plan Started'),
    ('monthly_start', 'Monthly Plan Started'),
    ('trial_quarterly_start', 'Trial - Quarterly Plan Started'),
    ('quarterly_start', 'Quarterly Plan Started'),
    ('trial_yearly_start', 'Trial - Yearly Plan Started'),
    ('yearly_start', 'Yearly Plan Started'),

    # 🟡 Reactivations
    ('reactivate_monthly', 'Reactivated - Monthly Plan'),
    ('reactivate_quarterly', 'Reactivated - Quarterly Plan'),
    ('reactivate_yearly', 'Reactivated - Yearly Plan'),

    # 🔴 Cancellations
    ('cancel_trial', 'Canceled - Trial Plan'),
    ('cancel_monthly', 'Canceled - Monthly Plan'),
    ('cancel_quarterly', 'Canceled - Quarterly Plan'),
    ('cancel_yearly', 'Canceled - Yearly Plan'),

    # 💵 Refunds
    ('refund_full', 'Full Refund Issued'),
    ('refund_partial', 'Partial Refund Issued'),

    # 🧾 Stripe Events
    ('stripe_payment_succeeded', 'Stripe Payment Succeeded'),
    ('stripe_payment_failed', 'Stripe Payment Failed'),
]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    event_type = models.CharField(max_length=50)  # e.g. 'trial_monthly_start'
    plan_name = models.CharField(max_length=50)  # 'adminMonthly', etc.
    is_trial = models.BooleanField(default=False)
    stripe_transaction_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)  # for future Stripe data dumps or internal logs

    def __str__(self):
        return f"{self.user.email} | {self.event_type} | {self.timestamp.strftime('%Y-%m-%d')}"
    # 👉 returns a readable string for this record, using either the user's email or linked user object


# 👉 summary:
# stores a complete history of major admin account lifecycle events, including signups, cancellations,
# and stripe payments. designed to ensure accurate billing history, prevent abuse,
# and support auditability across the subscription system.