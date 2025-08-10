from django.db import models
import uuid

class AdminIdentity(models.Model):
    adminID = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    admin_email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.admin_email} ({self.adminID})"
