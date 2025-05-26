import uuid  # 👉 used to generate a unique token for each signup
from django.db import models  # 👉 provides base model functionality

class PendingSignup(models.Model):  # 👉 stores pending admin signups after stripe checkout, before registration is complete
    email = models.EmailField()  # 👉 email address submitted during checkout
    session_id = models.CharField(max_length=255, unique=True)  # 👉 stripe session id used to track the payment
    token = models.CharField(max_length=64, unique=True, default=uuid.uuid4)  # 👉 unique token used to complete registration
    plan = models.CharField(max_length=50)  # 👉 name of the plan selected (e.g. admin_trial, admin_monthly)
    subscription_id = models.CharField(max_length=100, null=True, blank=True)  # 👉 stripe subscription id (set for paid plans)
    stripe_customer_id = models.CharField(max_length=100, null=True, blank=True)  # 👉 stripe customer id
    stripe_transaction_id = models.CharField(max_length=100, null=True, blank=True)  # 👉 optional charge or invoice id
    is_used = models.BooleanField(default=False)  # 👉 tracks whether the registration token has been used
    created_at = models.DateTimeField(auto_now_add=True)  # 👉 timestamp when this pending signup was created

    def __str__(self):
        return f"{self.email} ({self.plan})"  # 👉 displays email and plan in admin or logs

# 👉 summary:
# holds temporary signup data for admins after stripe checkout and before account creation.
# ensures that only verified and paid users can register, and that signup tokens are unique and one-time use.