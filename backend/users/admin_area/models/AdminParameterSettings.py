from django.db import models

from users.admin_area.configs.admin_parameter_defaults import get_admin_parameter_defaults_v1


class AdminParameterSettings(models.Model):
    admin = models.OneToOneField(
        "AdminIdentity",
        on_delete=models.CASCADE,
        related_name="parameter_settings",
    )
    initialized = models.BooleanField(default=False, db_index=True)
    defaults_version_applied = models.CharField(max_length=20, default="v1")
    parameters_json = models.JSONField(default=get_admin_parameter_defaults_v1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)
        verbose_name = "Admin Parameter Settings"
        verbose_name_plural = "Admin Parameter Settings"

    def __str__(self):
        return f"{self.admin.admin_email} | initialized={self.initialized} | {self.defaults_version_applied}"

