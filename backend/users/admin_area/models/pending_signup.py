import uuid
from django.db import models

class PendingSignup(models.Model):
    email = models.EmailField()
    session_id = models.CharField(max_length=255, unique=True)
    token = models.CharField(max_length=64, unique=True, default=uuid.uuid4)
    plan = models.CharField(max_length=50)
    subscription_id = models.CharField(max_length=100, null=True, blank=True)
    stripe_customer_id = models.CharField(max_length=100, null=True, blank=True)
    stripe_transaction_id = models.CharField(max_length=100, null=True, blank=True)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.email} ({self.plan})"

