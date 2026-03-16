from django.db import models


class GoalChoices(models.TextChoices):
    LOSE = "lose", "Lose Weight"
    MAINTAIN = "maintain", "Maintain Weight"
    GAIN = "gain", "Gain Weight"


class MacroPlanDefaultBase(models.Model):
    version = models.CharField(max_length=20, default="v1", db_index=True)
    goal = models.CharField(max_length=20, choices=GoalChoices.choices, db_index=True)
    protein_factor_unit = models.CharField(max_length=20, default="g_per_lb")
    protein_factor_value = models.DecimalField(max_digits=8, decimal_places=3, default=1)
    meal_macro_distribution_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TDEEDefault(models.Model):
    version = models.CharField(max_length=20, unique=True)
    lose_weight_percent = models.DecimalField(max_digits=6, decimal_places=2, default=-15)
    maintain_weight_percent = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    gain_weight_percent = models.DecimalField(max_digits=6, decimal_places=2, default=20)
    category_multipliers_json = models.JSONField(default=dict, blank=True)
    category_mapping_by_lifestyle_and_training_days_json = models.JSONField(default=dict, blank=True)
    weekly_day_multiplier_splits_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("version",)
        verbose_name = "TDEE Default"
        verbose_name_plural = "TDEE Defaults"

    def __str__(self):
        return f"TDEE Defaults ({self.version})"


class StandardDefault(MacroPlanDefaultBase):
    carb_percent = models.DecimalField(max_digits=6, decimal_places=3, default=60)
    fat_percent = models.DecimalField(max_digits=6, decimal_places=3, default=40)

    class Meta:
        ordering = ("version", "created_at")
        verbose_name = "Standard Default"
        verbose_name_plural = "Standard Defaults"
        constraints = [
            models.UniqueConstraint(
                fields=("version", "goal"),
                name="core_standard_default_version_goal_uniq",
            )
        ]

    def __str__(self):
        return f"Standard Defaults ({self.version}) - {self.goal}"


class KetoDefault(MacroPlanDefaultBase):
    carb_percent = models.DecimalField(max_digits=6, decimal_places=3, default=10)
    fat_percent = models.DecimalField(max_digits=6, decimal_places=3, default=90)

    class Meta:
        ordering = ("version", "created_at")
        verbose_name = "Keto Default"
        verbose_name_plural = "Keto Defaults"
        constraints = [
            models.UniqueConstraint(
                fields=("version", "goal"),
                name="core_keto_default_version_goal_uniq",
            )
        ]

    def __str__(self):
        return f"Keto Defaults ({self.version}) - {self.goal}"


class CarbCyclingDefault(MacroPlanDefaultBase):
    low_day_carb_percent = models.DecimalField(max_digits=6, decimal_places=3, default=20)
    low_day_fat_percent = models.DecimalField(max_digits=6, decimal_places=3, default=80)
    high_day_carb_percent = models.DecimalField(max_digits=6, decimal_places=3, default=80)
    high_day_fat_percent = models.DecimalField(max_digits=6, decimal_places=3, default=20)

    class Meta:
        ordering = ("version", "created_at")
        verbose_name = "Carb Cycling Default"
        verbose_name_plural = "Carb Cycling Defaults"
        constraints = [
            models.UniqueConstraint(
                fields=("version", "goal"),
                name="core_carb_cycling_default_version_goal_uniq",
            )
        ]

    def __str__(self):
        return f"Carb Cycling Defaults ({self.version}) - {self.goal}"
