from django.db import models
import uuid

class AdminIdentity(models.Model):
    adminID = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    admin_email = models.EmailField(unique=True)
    subdomain_slug = models.CharField(max_length=40, unique=True, null=True, blank=True)
    subdomain_locked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.admin_email} ({self.adminID})"
