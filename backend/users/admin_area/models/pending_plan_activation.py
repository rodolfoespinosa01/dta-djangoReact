from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class PendingPlanActivation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    plan_name = models.CharField(max_length=30)
    stripe_subscription_id = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    scheduled_start = models.DateTimeField()

    def is_due(self):
        return timezone.now() >= self.scheduled_start
