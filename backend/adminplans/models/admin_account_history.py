from django.db import models
from users.models.custom_user import CustomUser  # Reference to your custom user model

class AdminAccountHistory(models.Model):
    # Links each history entry to an admin user
    admin = models.ForeignKey(CustomUser, on_delete=models.CASCADE)

    # The plan name at the time (e.g., 'adminMonthly', 'adminAnnual')
    plan_name = models.CharField(max_length=30)

    # Stripe subscription ID for reference (can be null for older data or trials)
    subscription_id = models.CharField(max_length=100, null=True, blank=True)

    # When this subscription cycle started
    start_date = models.DateTimeField()

    # When it ended (or is scheduled to end); null if still active
    end_date = models.DateTimeField(null=True, blank=True)

    # Whether this plan was canceled before it naturally expired
    was_canceled = models.BooleanField(default=False)

    # Timestamp of when this history record was created
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        # Display readable info in Django admin or shell
        return f"{self.admin.email} - {self.plan_name} ({self.start_date.date()} to {self.end_date.date() if self.end_date else 'active'})"
