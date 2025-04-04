from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Subscription(models.Model):
    PLAN_CHOICES = (
        ('monthly', 'Monthly'),
        ('annual', 'Annual'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)  # Admin only
    stripe_subscription_id = models.CharField(max_length=255)
    plan_type = models.CharField(max_length=10, choices=PLAN_CHOICES)
    status = models.CharField(max_length=50)  # active, trialing, canceled, etc.
    current_period_end = models.DateTimeField()
    trial_used = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.plan_type}"
