from django.db import models
from django.utils import timezone
from core.models import CustomUser
from users.admin_area.models.plan import Plan

class ScheduledSubscription(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="scheduled_subscriptions")
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    starts_on = models.DateTimeField()
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_transaction_id = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.user.email} → {self.plan.name} on {self.starts_on.strftime('%Y-%m-%d')}"
