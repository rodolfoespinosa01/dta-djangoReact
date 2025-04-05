from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('client', 'Client'),
        ('superadmin', 'SuperAdmin'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    subscription_status = models.CharField(max_length=20, default='inactive')  # or trial/active/etc.

    def is_admin_user(self):
        return self.role == 'admin'
