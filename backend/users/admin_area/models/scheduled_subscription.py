from django.db import models  # 👉 provides base model functionality
from django.utils import timezone  # 👉 used for datetime operations (not used directly here but good to keep for future logic)
from core.models import CustomUser  # 👉 imports the custom user model
from users.admin_area.models.plan import Plan  # 👉 imports the subscription plan model

class ScheduledSubscription(models.Model):  # 👉 stores future-dated subscription changes for users
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="scheduled_subscriptions")  
    # 👉 links the scheduled subscription to a specific user

    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)  
    # 👉 the plan that will be activated when the scheduled date is reached

    created_at = models.DateTimeField(auto_now_add=True)  
    # 👉 timestamp of when this record was created

    starts_on = models.DateTimeField()  
    # 👉 the future date when this plan should become active

    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)  
    # 👉 optional stripe subscription id associated with the upcoming plan

    stripe_transaction_id = models.CharField(max_length=255, blank=True, null=True)  
    # 👉 optional stripe payment or invoice id for tracking the charge

    def __str__(self):
        return f"{self.user.email} → {self.plan.name} on {self.starts_on.strftime('%Y-%m-%d')}"  
    # 👉 displays a readable summary of the scheduled change (used in admin or logs)


# 👉 summary:
# stores subscriptions that are scheduled to activate at a future date,
# often used after a downgrade or upgrade is confirmed but should take effect after
# the current billing cycle. helps support accurate plan transitions and billing automation.