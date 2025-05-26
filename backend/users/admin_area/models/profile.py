from django.db import models  # 👉 provides base model functionality
from django.conf import settings  # 👉 allows access to the project's custom user model setting
from users.admin_area.models import Plan  # 👉 imports the subscription plan model


class Profile(models.Model):  # 👉 stores subscription details tied to a user over time (historical + active)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profiles")  
    # 👉 links to the custom user model, one user can have multiple profiles

    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True)  
    # 👉 references the plan the user is on during this subscription cycle

    
    is_active = models.BooleanField(default=True)  # 👉 legacy flag to show if the profile is still considered valid
    is_canceled = models.BooleanField(default=False)  # 👉 tracks if the user canceled during this cycle (used for frontend logic)
    is_current = models.BooleanField(default=True)  # 👉 marks the currently active profile (only one per user should be true)

    subscription_start_date = models.DateTimeField()  # 👉 when this subscription period began
    subscription_end_date = models.DateTimeField(null=True, blank=True)  # 👉 when the plan ended or will end
    next_billing_date = models.DateTimeField(null=True, blank=True)  # 👉 when the next payment is scheduled (used for paid plans)

    stripe_subscription_id = models.CharField(max_length=255, null=True, blank=True)  # 👉 id from stripe for subscription tracking
    stripe_transaction_id = models.CharField(max_length=255, null=True, blank=True)  # 👉 last processed payment/charge id
    stripe_customer_id = models.CharField(max_length=255, null=True, blank=True)  # 👉 stripe customer id for this user

    created_at = models.DateTimeField(auto_now_add=True)  # 👉 timestamp when this profile record was created

    def __str__(self):
        return f"{self.user.email} | {self.plan.name if self.plan else 'No Plan'} | Current: {self.is_current}"
    # 👉 displays a readable summary of the user’s profile with plan and status


# 👉 summary:
# tracks individual subscription cycles for admin users, including stripe info, billing dates,
# and plan status. supports reactivation, upgrades, and billing history by allowing multiple
# profiles per user while keeping one marked as current.