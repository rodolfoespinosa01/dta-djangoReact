import uuid
from django.db import models

class AdminPlan(models.Model):
    PLAN_CHOICES = [
        ('adminTrial', 'Free Admin Trial'),
        ('adminMonthly', 'Monthly Admin Plan'),
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
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.email} ({self.plan})"
