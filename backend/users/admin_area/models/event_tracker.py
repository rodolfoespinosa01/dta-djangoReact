from django.db import models
from django.utils import timezone
from .admin_identity import AdminIdentity  # FK to uniquely track admin-level events


class EventTracker(models.Model):
    admin = models.ForeignKey('AdminIdentity', on_delete=models.CASCADE, related_name='event_logs')
    event_type = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True, null=True)

    def __str__(self):
        return str(self.admin.id)