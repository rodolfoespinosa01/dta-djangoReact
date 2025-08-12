from django.db import models
from users.admin_area.models import AdminIdentity  # Make sure this is correct

class PreCheckout(models.Model):
    admin = models.ForeignKey(
        AdminIdentity,
        on_delete=models.CASCADE,
        related_name="precheckouts",
        null=True  
    )

    plan_name = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    is_trial = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.admin.admin_email} - {self.plan_name} - {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
