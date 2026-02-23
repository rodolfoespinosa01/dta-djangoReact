from django.conf import settings
from django.db import models

from users.admin_area.models import AdminIdentity


class ClientPendingSignup(models.Model):
    OFFER_CHOICES = [
        ("macro_calculator_free", "Macro Calculator (Free)"),
        ("food_plan_weekly", "Food Plan Weekly"),
        ("food_plan_monthly", "Food Plan Monthly"),
    ]
    SALE_CHANNEL_CHOICES = [
        ("dta_direct", "DTA Direct"),
        ("admin_white_label", "Admin White Label"),
    ]

    email = models.EmailField(db_index=True)
    token = models.CharField(max_length=128, unique=True, db_index=True)
    admin = models.ForeignKey(
        AdminIdentity,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="client_pending_signups",
    )
    sale_channel = models.CharField(max_length=32, choices=SALE_CHANNEL_CHOICES, default="admin_white_label")
    offer_code = models.CharField(max_length=64, choices=OFFER_CHOICES)
    billing_cycle = models.CharField(max_length=20, blank=True, default="")
    trial_days = models.PositiveIntegerField(default=0)
    amount_cents = models.PositiveIntegerField(default=0)
    includes_food_plan = models.BooleanField(default=False)
    includes_coaching = models.BooleanField(default=False)
    registration_link_printed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Client Pending Signup"
        verbose_name_plural = "Client Pending Signups"

    def __str__(self):
        return f"{self.email} | {self.offer_code}"


class ClientMacroAccessLink(models.Model):
    STATUS_CHOICES = [
        ("not_started", "Not Started"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
    ]
    SALE_CHANNEL_CHOICES = [
        ("dta_direct", "DTA Direct"),
        ("admin_white_label", "Admin White Label"),
    ]

    email = models.EmailField(db_index=True)
    token = models.CharField(max_length=128, unique=True, db_index=True)
    admin = models.ForeignKey(
        AdminIdentity,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="client_macro_access_links",
    )
    sale_channel = models.CharField(max_length=32, choices=SALE_CHANNEL_CHOICES, default="admin_white_label")
    questionnaire_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="not_started", db_index=True)
    questionnaire_current_step = models.CharField(max_length=64, blank=True, default="")
    questionnaire_answers_json = models.JSONField(default=dict, blank=True)
    questionnaire_completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_opened_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Client Macro Access Link"
        verbose_name_plural = "Client Macro Access Links"

    def __str__(self):
        return f"{self.email} | macro-access"


class ClientProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="client_profile")
    associated_admin = models.ForeignKey(
        AdminIdentity,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="clients",
    )
    sale_channel = models.CharField(max_length=32, default="admin_white_label")
    offer_code = models.CharField(max_length=64)
    billing_cycle = models.CharField(max_length=20, blank=True, default="")
    trial_days = models.PositiveIntegerField(default=0)
    amount_cents = models.PositiveIntegerField(default=0)
    includes_food_plan = models.BooleanField(default=False)
    includes_coaching = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Client Profile"
        verbose_name_plural = "Client Profiles"

    def __str__(self):
        return f"{self.user.email} | {self.offer_code}"


class ClientQuestionnaireProgress(models.Model):
    STATUS_CHOICES = [
        ("not_started", "Not Started"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="questionnaire_progress")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="not_started", db_index=True)
    current_step = models.CharField(max_length=64, blank=True, default="")
    answers_json = models.JSONField(default=dict, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)
        verbose_name = "Client Questionnaire Progress"
        verbose_name_plural = "Client Questionnaire Progress"

    def __str__(self):
        return f"{self.user.email} | {self.status}"


class ClientMealComboSelection(models.Model):
    DAY_CHOICES = [
        ("sunday", "Sunday"),
        ("monday", "Monday"),
        ("tuesday", "Tuesday"),
        ("wednesday", "Wednesday"),
        ("thursday", "Thursday"),
        ("friday", "Friday"),
        ("saturday", "Saturday"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="meal_combo_selections")
    day_of_week = models.CharField(max_length=12, choices=DAY_CHOICES, db_index=True)
    meal_number = models.PositiveSmallIntegerField()
    combo_template = models.ForeignKey(
        "core.MealComboTemplate",
        to_field="combo_id",
        db_column="combo_id",
        on_delete=models.PROTECT,
        related_name="client_meal_selections",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("user_id", "day_of_week", "meal_number")
        verbose_name = "Client Meal Combo Selection"
        verbose_name_plural = "Client Meal Combo Selections"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "day_of_week", "meal_number"],
                name="client_unique_day_meal_combo_selection",
            )
        ]

    def __str__(self):
        return f"{self.user.email} | {self.day_of_week} meal {self.meal_number} -> combo {self.combo_template_id}"


class ClientFoodPreferenceChangeLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="food_preference_change_logs")
    client_profile = models.ForeignKey(
        "ClientProfile",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="food_preference_change_logs",
    )
    before_json = models.JSONField(default=dict, blank=True)
    after_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Client Food Preference Change Log"
        verbose_name_plural = "Client Food Preference Change Logs"

    def __str__(self):
        return f"{self.user.email} | food-pref change @ {self.created_at}"
