# backend/users/models/account_history.py

from django.db import models
from django.utils import timezone
from users.models import CustomUser

class AccountHistory(models.Model):
    PLAN_CHOICES = [
        ('adminTrial', 'Free Trial'),
        ('adminMonthly', 'Monthly Plan'),
        ('adminQuarterly', 'Quarterly Plan'),
        ('adminAnnual', 'Annual Plan'),
    ]

    STATUS_CHOICES = [
        ('started', 'Started'),
        ('upgraded', 'Upgraded'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='account_history')
    plan_type = models.CharField(max_length=20, choices=PLAN_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    timestamp = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.email} | {self.plan_type} | {self.status} | {self.timestamp.strftime('%Y-%m-%d')}"
