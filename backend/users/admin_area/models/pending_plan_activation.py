from django.db import models  # 👉 provides base model functionality
from django.contrib.auth import get_user_model  # 👉 allows dynamic access to the custom user model
from django.utils import timezone  # 👉 used for comparing timestamps like scheduled_start

User = get_user_model()  # 👉 loads the currently active custom user model

class PendingPlanActivation(models.Model):  # 👉 stores scheduled plan upgrades for users
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # 👉 links the pending activation to a user
    plan_name = models.CharField(max_length=30)  # 👉 stores the name of the plan to be activated
    stripe_subscription_id = models.CharField(max_length=100, null=True, blank=True)  # 👉 optionally links to a stripe subscription
    created_at = models.DateTimeField(auto_now_add=True)  # 👉 records when this record was created
    scheduled_start = models.DateTimeField()  # 👉 when the new plan should go into effect

    def is_due(self):
        return timezone.now() >= self.scheduled_start  # 👉 returns true if it's time to activate the plan



# 👉 summary:
# tracks future-dated plan activations after a user reactivates or changes subscriptions.
# used to delay the creation of a new profile until the current billing period ends.