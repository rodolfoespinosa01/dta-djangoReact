from django.db import models
from django.utils import timezone
from users.models.custom_user import CustomUser  # Reference to your custom user model

class AdminProfile(models.Model):
    # One-to-one link to the admin user (each admin gets one active profile per subscription cycle)
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='admin_profile')

    # For trial users: date when trial started
    trial_start_date = models.DateTimeField(null=True, blank=True)

    # Timestamp when the current active subscription started (trial or paid)
    subscription_started_at = models.DateTimeField(null=True, blank=True)

    # The next expected billing date (used for countdowns, Stripe sync, UI display)
    next_billing_date = models.DateTimeField(null=True, blank=True)

    # Stripe customer ID for this admin (used in webhook lookups, billing management)
    admin_stripe_customer_id = models.CharField(max_length=100, null=True, blank=True)

    # Stripe subscription ID for this plan (used to cancel/reactivate)
    admin_stripe_subscription_id = models.CharField(max_length=100, null=True, blank=True)

    # Set to True if admin cancels auto-renew (but access is still active until end of cycle)
    auto_renew_cancelled = models.BooleanField(default=False)

    # Flag that marks if the admin canceled entirely (used to block access after end date)
    is_canceled = models.BooleanField(default=False)

    # When the admin canceled their plan
    canceled_at = models.DateTimeField(null=True, blank=True)

    # The actual end date of access (used instead of `next_billing_date` after cancellation)
    subscription_end_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        # Display useful admin status in Django admin or logs
        return f"{self.user.email} - {self.user.subscription_status}"

    def trial_days_remaining(self):
        # Calculates how many trial days are left (0 if expired)
        if not self.trial_start_date:
            return None
        elapsed = timezone.now() - self.trial_start_date
        remaining = 14 - elapsed.days
        return max(0, remaining)

    def is_trial_expired(self):
        # Returns True if trial has expired
        return self.trial_days_remaining() == 0
