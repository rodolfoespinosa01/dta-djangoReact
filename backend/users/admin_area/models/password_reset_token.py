from django.db import models  # 👉 provides base model functionality
from django.utils import timezone  # 👉 used to calculate time-based logic
from core.models import CustomUser  # 👉 imports the custom user model

class PasswordResetToken(models.Model):  # 👉 stores password reset tokens for users
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)  # 👉 links token to a specific user
    token = models.CharField(max_length=64)  # 👉 stores the unique reset token string
    created_at = models.DateTimeField(auto_now_add=True)  # 👉 stores when the token was created


    def is_expired(self):
        return timezone.now() - self.created_at > timezone.timedelta(hours=24)
    # 👉 returns true if the token is older than 24 hours (used to invalidate expired tokens)

    def __str__(self):
        return f"Token for {self.user.email}"
    # 👉 shows a readable description in the admin or logs

# 👉 summary:
# stores password reset tokens tied to users and includes logic to auto-expire them after 24 hours.
# used in the forgot password flow to validate reset requests securely.