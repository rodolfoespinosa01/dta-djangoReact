from django.db import models

from core.models import GoalChoices


class AdminMacroPlanSettingsBase(models.Model):
    defaults_version_applied = models.CharField(max_length=20, default="v1")
    goal = models.CharField(max_length=20, choices=GoalChoices.choices, db_index=True)
    protein_factor_unit = models.CharField(max_length=20, default="g_per_lb")
    protein_factor_value = models.DecimalField(max_digits=8, decimal_places=3, default=1)
    meal_macro_distribution_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AdminTDEESettings(models.Model):
    admin = models.OneToOneField(
        "AdminIdentity",
        on_delete=models.CASCADE,
        related_name="tdee_settings",
    )
    initialized = models.BooleanField(default=True, db_index=True)
    defaults_version_applied = models.CharField(max_length=20, default="v1")
    lose_weight_percent = models.DecimalField(max_digits=6, decimal_places=2, default=-15)
    maintain_weight_percent = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    gain_weight_percent = models.DecimalField(max_digits=6, decimal_places=2, default=20)
    category_multipliers_json = models.JSONField(default=dict, blank=True)
    category_mapping_by_lifestyle_and_training_days_json = models.JSONField(default=dict, blank=True)
    weekly_day_multiplier_splits_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("admin__admin_email",)
        verbose_name = "TDEE Settings"
        verbose_name_plural = "TDEE Settings"

    def __str__(self):
        return f"TDEE Settings - {self.admin.admin_email}"


class AdminStandardSettings(AdminMacroPlanSettingsBase):
    admin = models.ForeignKey(
        "AdminIdentity",
        on_delete=models.CASCADE,
        related_name="standard_settings_rows",
    )
    carb_percent = models.DecimalField(max_digits=6, decimal_places=3, default=60)
    fat_percent = models.DecimalField(max_digits=6, decimal_places=3, default=40)

    class Meta:
        ordering = ("admin__admin_email", "created_at")
        verbose_name = "Standard Settings"
        verbose_name_plural = "Standard Settings"
        constraints = [
            models.UniqueConstraint(
                fields=("admin", "goal"),
                name="admin_standard_settings_admin_goal_uniq",
            )
        ]

    def __str__(self):
        return f"Standard Settings - {self.admin.admin_email} - {self.goal}"


class AdminKetoSettings(AdminMacroPlanSettingsBase):
    admin = models.ForeignKey(
        "AdminIdentity",
        on_delete=models.CASCADE,
        related_name="keto_settings_rows",
    )
    carb_percent = models.DecimalField(max_digits=6, decimal_places=3, default=10)
    fat_percent = models.DecimalField(max_digits=6, decimal_places=3, default=90)

    class Meta:
        ordering = ("admin__admin_email", "created_at")
        verbose_name = "Keto Settings"
        verbose_name_plural = "Keto Settings"
        constraints = [
            models.UniqueConstraint(
                fields=("admin", "goal"),
                name="admin_keto_settings_admin_goal_uniq",
            )
        ]

    def __str__(self):
        return f"Keto Settings - {self.admin.admin_email} - {self.goal}"


class AdminCarbCyclingSettings(AdminMacroPlanSettingsBase):
    admin = models.ForeignKey(
        "AdminIdentity",
        on_delete=models.CASCADE,
        related_name="carb_cycling_settings_rows",
    )
    low_day_carb_percent = models.DecimalField(max_digits=6, decimal_places=3, default=20)
    low_day_fat_percent = models.DecimalField(max_digits=6, decimal_places=3, default=80)
    high_day_carb_percent = models.DecimalField(max_digits=6, decimal_places=3, default=80)
    high_day_fat_percent = models.DecimalField(max_digits=6, decimal_places=3, default=20)

    class Meta:
        ordering = ("admin__admin_email", "created_at")
        verbose_name = "Carb Cycling Settings"
        verbose_name_plural = "Carb Cycling Settings"
        constraints = [
            models.UniqueConstraint(
                fields=("admin", "goal"),
                name="admin_carb_cycling_settings_admin_goal_uniq",
            )
        ]

    def __str__(self):
        return f"Carb Cycling Settings - {self.admin.admin_email} - {self.goal}"