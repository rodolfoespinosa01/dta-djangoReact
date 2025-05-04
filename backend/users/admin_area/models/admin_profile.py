from django.db import models
from django.utils import timezone
from core.models import CustomUser

class AdminProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='admin_profile')
    trial_start_date = models.DateTimeField(null=True, blank=True)
    subscription_started_at = models.DateTimeField(null=True, blank=True)
    next_billing_date = models.DateTimeField(null=True, blank=True)
    admin_stripe_customer_id = models.CharField(max_length=100, null=True, blank=True)
    admin_stripe_subscription_id = models.CharField(max_length=100, null=True, blank=True)
    auto_renew_cancelled = models.BooleanField(default=False)
    is_canceled = models.BooleanField(default=False)
    canceled_at = models.DateTimeField(null=True, blank=True)
    subscription_end_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.email} - {self.user.subscription_status}"

    def trial_days_remaining(self):
        if not self.trial_start_date:
            return None
        elapsed = timezone.now() - self.trial_start_date
        remaining = 14 - elapsed.days
        return max(0, remaining)

    def is_trial_expired(self):
        return self.trial_days_remaining() == 0
