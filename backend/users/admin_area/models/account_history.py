from django.db import models  # 👉 provides access to django model classes and fields
from django.contrib.auth import get_user_model  # 👉 allows referencing the custom user model dynamically

User = get_user_model()  # 👉 gets the project's configured custom user model


class AccountHistory(models.Model):  # 👉 stores a history log of user account events (signup, cancel, etc.)

    EVENT_CHOICES = [
        ('signup', 'Signup'),
        ('cancel', 'Cancel Subscription'),
        ('stripe_payment', 'Stripe Payment Processed'),
    ]
    # 👉 defines the allowed types of events recorded in the history

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    # 👉 links the event to a user (nullable in case of pre-signup events)

    email = models.EmailField(null=True, blank=True)
    # 👉 stores email separately in case the user record doesn't exist yet

    event_type = models.CharField(max_length=20, choices=EVENT_CHOICES)
    # 👉 indicates the type of event being logged

    plan_name = models.CharField(max_length=30)
    # 👉 stores the name of the plan tied to the event (e.g. admin_monthly)

    payment_processed_on = models.DateTimeField(null=True, blank=True)
    # 👉 records when a stripe payment was completed


    subscription_start = models.DateTimeField(null=True, blank=True)
    # 👉 timestamp of when a subscription period begins

    subscription_end = models.DateTimeField(null=True, blank=True)
    # 👉 timestamp of when the subscription period ends or was canceled

    cancelled_at = models.DateTimeField(null=True, blank=True)
    # 👉 timestamp of when the user canceled their plan

    timestamp = models.DateTimeField(auto_now_add=True)
    # 👉 records when this history record was created

    stripe_transaction_id = models.CharField(max_length=255, blank=True, null=True)


    def __str__(self):
        if self.email:
            return f"{self.email} - {self.event_type} on {self.timestamp.strftime('%Y-%m-%d')}"
        elif self.user:
            return f"{self.user.email} - {self.event_type} on {self.timestamp.strftime('%Y-%m-%d')}"
        return f"Unlinked - {self.event_type} on {self.timestamp.strftime('%Y-%m-%d')}"
    # 👉 returns a readable string for this record, using either the user's email or linked user object


# 👉 summary:
# stores a complete history of major admin account lifecycle events, including signups, cancellations,
# and stripe payments. designed to ensure accurate billing history, prevent abuse,
# and support auditability across the subscription system.