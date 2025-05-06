from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class AccountHistory(models.Model):
    EVENT_CHOICES = [
        ('signup', 'Signup'),
        ('cancel', 'Cancel Subscription'),
        ('reactivate', 'Reactivation'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event_type = models.CharField(max_length=20, choices=EVENT_CHOICES)
    plan_name = models.CharField(max_length=30)  # e.g. 'adminMonthly'
    stripe_subscription_id = models.CharField(max_length=100, null=True, blank=True)
    
    subscription_start = models.DateTimeField(null=True, blank=True)
    subscription_end = models.DateTimeField(null=True, blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.event_type} - {self.timestamp.strftime('%Y-%m-%d')}"
