import uuid
from django.db import models

class AdminPendingSignup(models.Model):
    # Email of the admin trying to register
    email = models.EmailField()

    # Stripe session ID tied to this registration attempt (from checkout)
    session_id = models.CharField(max_length=255, unique=True)

    # Unique token to validate registration (used only once)
    token = models.CharField(max_length=64, unique=True, default=uuid.uuid4)

    # Plan name selected (e.g. 'adminTrial', 'adminMonthly', etc.)
    plan = models.CharField(max_length=50)

    # Optional Stripe subscription ID (available after checkout)
    subscription_id = models.CharField(max_length=100, null=True, blank=True)

    # Timestamp when this entry was created (useful for expiration checks)
    created_at = models.DateTimeField(auto_now_add=True)

    # Tracks whether the token was already used to register
    is_used = models.BooleanField(default=False)

    def __str__(self):
        # Display useful info in admin or logs
        return f"{self.email} ({self.plan})"
