from django.db import models  # 👉 provides base model functionality for defining database tables

class PreCheckoutEmail(models.Model):  # 👉 stores emails submitted before stripe checkout begins
    email = models.EmailField(unique=True)  # 👉 the user's email, must be unique to avoid duplicates
    plan_name = models.CharField(max_length=50)  # 👉 the plan the user selected (e.g., adminTrial, adminMonthly, etc.)
    created_at = models.DateTimeField(auto_now_add=True, null =True)  # 👉 timestamp of when the email was collected
    is_trial = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.email} - {self.plan_name} - {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"

    # 👉 summary:
    # captures emails from users before they start the stripe checkout flow.
    # now also stores the selected plan_name for context, analytics, and future filtering.
