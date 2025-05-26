from django.contrib.auth.models import AbstractUser # 👉 imports django’s built-in user class, which we’re extending
from django.db import models # 👉 gives access to all django model field types
from django.utils import timezone # 👉 used for time-based fields (not currently used here)


class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('client', 'Client'),
        ('superadmin', 'SuperAdmin'),
    )
    # 👆 defines user role options stored as strings in the database

    SUBSCRIPTION_CHOICES = [
        ('admin_trial', 'Admin Free Trial'),
        ('admin_monthly', 'Admin Monthly'),
        ('admin_annual', 'Admin Annual'),
        ('admin_inactive', 'Admin Inactive'),
    ]
    # 👆 defines plan options for tracking the user's subscription status

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    # 👆 saves the user's role using one of the predefined role choices

    subscription_status = models.CharField(
        max_length=30,
        choices=SUBSCRIPTION_CHOICES,
        default='admin_inactive'
    )
    # 👆 saves the user’s current plan status with a default of inactive

    stripe_customer_id = models.CharField(max_length=100, null=True, blank=True)
    # 👆 stores the user's stripe customer id (used for billing lookup)

    def __str__(self):
        return self.username
    # 👆 tells django to show the username when this user object is printed or listed (e.g., in the admin panel)


# 👉 summary:
# defines the custom user model used across the project.
# extends django’s default user with role-based access control,
# subscription tracking, and stripe customer id integration.
# required for authentication, billing, and user role management.
