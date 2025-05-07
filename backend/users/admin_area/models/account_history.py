from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class AccountHistory(models.Model):
    EVENT_CHOICES = [
        ('signup', 'Signup'),
        ('cancel', 'Cancel Subscription'),
        ('reactivate', 'Reactivation'),
        ('stripe_payment', 'Stripe Payment Processed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)  # Used when user doesn't exist yet
    event_type = models.CharField(max_length=20, choices=EVENT_CHOICES)
    plan_name = models.CharField(max_length=30)
    
    payment_processed_on = models.DateTimeField(null=True, blank=True)
    stripe_transaction_id = models.CharField(max_length=100, null=True, blank=True)
    stripe_customer_id = models.CharField(max_length=100, null=True, blank=True)
    stripe_subscription_id = models.CharField(max_length=100, null=True, blank=True)

    subscription_start = models.DateTimeField(null=True, blank=True)
    subscription_end = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    reactivated_on = models.DateTimeField(null=True, blank=True)

    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.email:
            return f"{self.email} - {self.event_type} on {self.timestamp.strftime('%Y-%m-%d')}"
        elif self.user:
            return f"{self.user.email} - {self.event_type} on {self.timestamp.strftime('%Y-%m-%d')}"
        return f"Unlinked - {self.event_type} on {self.timestamp.strftime('%Y-%m-%d')}"



