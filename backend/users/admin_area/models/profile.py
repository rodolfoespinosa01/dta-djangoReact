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
    is_trial = models.BooleanField(default=False)  # 👉 marks this subscription as a trial period or not
    trial_start = models.DateTimeField(null=True, blank=True)  # 👉 when the trial period began (if applicable)

    subscription_start = models.DateTimeField(null=True, blank=True)
    subscription_end = models.DateTimeField(null=True, blank=True)  # 👉 when the plan ended or will end
    next_billing = models.DateTimeField(null=True, blank=True)  # 👉 when the next payment is scheduled (used for paid plans)

    stripe_transaction_id = models.CharField(max_length=255, null=True, blank=True)  # 👉 last processed payment/charge id

    created_at = models.DateTimeField(auto_now_add=True)  # 👉 timestamp when this profile record was created

    def __str__(self):
        return f"{self.user.email} | {self.plan.name if self.plan else 'No Plan'} | Current: {self.is_active}"
    # 👉 displays a readable summary of the user’s profile with plan and status


# 👉 summary:
# tracks individual subscription cycles for admin users, including stripe info, billing dates,
# and plan status. 