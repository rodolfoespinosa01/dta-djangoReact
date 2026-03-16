from django.db import models


class AdminParameterSettingsChangeLog(models.Model):
    ACTION_CHOICES = (
        ("use_defaults", "Use Defaults"),
        ("manual_save", "Manual Save"),
    )

    admin = models.ForeignKey(
        "AdminIdentity",
        on_delete=models.CASCADE,
        related_name="parameter_settings_change_logs",
    )
    action = models.CharField(max_length=32, choices=ACTION_CHOICES, db_index=True)
    changed_paths = models.JSONField(default=list, blank=True)
    before_json = models.JSONField(null=True, blank=True)
    after_json = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Admin Parameter Settings Change Log"
        verbose_name_plural = "Admin Parameter Settings Change Logs"

    def __str__(self):
        return f"{self.admin.admin_email} | {self.action} | {len(self.changed_paths or [])} changes"

