from django.db import models


class AdminAccountHistory(models.Model):
    admin = models.ForeignKey(
        "AdminIdentity",
        on_delete=models.CASCADE,
        related_name="account_history",
    )
    source_event = models.OneToOneField(
        "EventTracker",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="account_history_entry",
    )
    event_type = models.CharField(max_length=100, db_index=True)
    details = models.TextField(blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-occurred_at",)

    def __str__(self):
        return f"{self.admin.admin_email} | {self.event_type} | {self.occurred_at}"
