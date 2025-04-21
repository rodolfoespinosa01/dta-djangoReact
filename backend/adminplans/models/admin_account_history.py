from django.db import models
from users.models.custom_user import CustomUser

class AdminAccountHistory(models.Model):
    admin = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    plan_name = models.CharField(max_length=30)
    subscription_id = models.CharField(max_length=100, null=True, blank=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    was_canceled = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.admin.email} - {self.plan_name} ({self.start_date.date()} to {self.end_date.date() if self.end_date else 'active'})"
