from django.db import models
from django.utils import timezone
from core.models import CustomUser

class PasswordResetToken(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    token = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() - self.created_at > timezone.timedelta(hours=24)

    def __str__(self):
        return f"Token for {self.user.email}"
