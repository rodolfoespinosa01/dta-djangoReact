from django.db import models
from django.conf import settings
from users.admin_area.models import Plan

class Profile(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profiles")
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True)
    
    is_active = models.BooleanField(default=True)           # Legacy flag
    is_canceled = models.BooleanField(default=False)        # Used for frontend UX and logic
    is_current = models.BooleanField(default=True)          # Only one profile per user should have this = True

    subscription_start_date = models.DateTimeField()
    subscription_end_date = models.DateTimeField(null=True, blank=True)
    next_billing_date = models.DateTimeField(null=True, blank=True)

    stripe_subscription_id = models.CharField(max_length=255, null=True, blank=True)
    stripe_transaction_id = models.CharField(max_length=255, null=True, blank=True)
    stripe_customer_id = models.CharField(max_length=255, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} | {self.plan.name if self.plan else 'No Plan'} | Current: {self.is_current}"
