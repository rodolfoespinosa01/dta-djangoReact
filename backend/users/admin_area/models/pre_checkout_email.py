from django.db import models  # 👉 provides base model functionality for defining database tables

class PreCheckoutEmail(models.Model):  # 👉 stores emails submitted before stripe checkout begins
    email = models.EmailField(unique=True)  # 👉 the user's email, must be unique to avoid duplicates
    created_at = models.DateTimeField(auto_now_add=True)  # 👉 timestamp of when the email was collected

    def __str__(self):
        return self.email  # 👉 displays the email in admin or logs

    # 👉 summary:
    # captures emails from users before they start the stripe checkout flow.
    # used for tracking leads, preventing duplicate signups, and email remarketing.