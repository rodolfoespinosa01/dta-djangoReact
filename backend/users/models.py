from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('client', 'Client'),
        ('superadmin', 'SuperAdmin'),
    )

    SUBSCRIPTION_CHOICES = [
        ('admin_trial', 'Admin Free Trial'),
        ('admin_monthly', 'Admin Monthly'),
        ('admin_annual', 'Admin Annual'),
        ('admin_inactive', 'Admin Inactive'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    subscription_status = models.CharField(max_length=30, choices=SUBSCRIPTION_CHOICES, default='admin_inactive')

    def __str__(self):
        return self.username
    
class AdminPasswordResetToken(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    token = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() - self.created_at > timezone.timedelta(hours=24)
