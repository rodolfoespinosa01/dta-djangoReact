import uuid
from django.db import models
from django.utils import timezone
from users.models.custom_user import CustomUser

class AdminPlan(models.Model):
    PLAN_CHOICES = [
        ('adminTrial', 'Free Admin Trial'),
        ('adminMonthly', 'Monthly Admin Plan'),
        ('adminQuarterly', 'Quarterly Admin Plan'),
        ('adminAnnual', 'Annual Admin Plan'),
    ]

    name = models.CharField(max_length=30, choices=PLAN_CHOICES, unique=True)
    description = models.TextField()
    stripe_price_id = models.CharField(max_length=100)
    price_cents = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.get_name_display()

    def price_dollars(self):
        return round(self.price_cents / 100, 2)


class PendingAdminSignup(models.Model):
    email = models.EmailField()
    session_id = models.CharField(max_length=255, unique=True)
    token = models.CharField(max_length=64, unique=True, default=uuid.uuid4)
    plan = models.CharField(max_length=50)
    subscription_id = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.email} ({self.plan})"


class AdminProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='admin_profile')
    trial_start_date = models.DateTimeField(null=True, blank=True)
    subscription_started_at = models.DateTimeField(null=True, blank=True)
    next_billing_date = models.DateTimeField(null=True, blank=True)
    admin_stripe_customer_id = models.CharField(max_length=100, null=True, blank=True)
    admin_stripe_subscription_id = models.CharField(max_length=100, null=True, blank=True)
    auto_renew_cancelled = models.BooleanField(default=False)
    # Add these fields to support cancellation + reactivation logic
    is_canceled = models.BooleanField(default=False)
    canceled_at = models.DateTimeField(null=True, blank=True)
    subscription_end_date = models.DateTimeField(null=True, blank=True)  # used for paid admins only


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

class AdminAccountHistory(models.Model):
    admin = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    plan_name = models.CharField(max_length=30)
    subscription_id = models.CharField(max_length=100, null=True, blank=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    was_canceled = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.admin.email} - {self.plan_name} ({self.start_date.date()} to {self.end_date.date() if self.end_date else 'active'})"

