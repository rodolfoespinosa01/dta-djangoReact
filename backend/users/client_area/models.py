from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from users.admin_area.models import AdminIdentity


class ClientPendingSignup(models.Model):
    STATUS_PENDING = "pending"
    STATUS_COMPLETED = "completed"
    STATUS_EXPIRED = "expired"
    STATUS_SUPERSEDED = "superseded"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_EXPIRED, "Expired"),
        (STATUS_SUPERSEDED, "Superseded"),
    ]
    OFFER_CHOICES = [
        ("macro_calculator_free", "Macro Calculator (Free)"),
        ("food_plan_monthly", "Food Plan Monthly"),
        ("food_plan_monthly_premium", "Food Plan Monthly Premium"),
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
    registration_link = models.URLField(max_length=2048, blank=True, default="")
    expires_at = models.DateTimeField(null=True, blank=True)
    used_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    stripe_checkout_session_id = models.CharField(max_length=128, blank=True, default="", db_index=True)
    registration_link_printed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Client Pending Signup"
        verbose_name_plural = "Client Pending Signups"

    def __str__(self):
        return f"{self.email} | {self.offer_code}"

    @property
    def is_used(self):
        return self.used_at is not None

    @property
    def is_expired(self):
        return bool(self.expires_at and self.expires_at <= timezone.now())


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
    COACHING_TERM_CHOICES = [
        ("none", "No Coaching"),
        ("1_month", "1 Month Coaching"),
        ("3_months", "3 Months Coaching"),
    ]

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
    coaching_term = models.CharField(max_length=20, choices=COACHING_TERM_CHOICES, default="none")
    coaching_expires_at = models.DateTimeField(null=True, blank=True)
    stripe_customer_id = models.CharField(max_length=64, blank=True, default="")
    stripe_subscription_id = models.CharField(max_length=64, blank=True, default="")
    theme_preference = models.CharField(max_length=20, default="light")
    is_active = models.BooleanField(default=True)
    cancel_at_period_end = models.BooleanField(default=False)
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


class ClientQueuedPlanChange(models.Model):
    STATUS_CHOICES = [
        ("queued", "Queued"),
        ("applied", "Applied"),
        ("canceled", "Canceled"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="queued_plan_changes")
    client_profile = models.ForeignKey(
        "ClientProfile",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="queued_plan_changes",
    )
    target_offer_code = models.CharField(max_length=64)
    target_coaching_term = models.CharField(max_length=20, default="none")
    amount_cents = models.PositiveIntegerField(default=0)
    queued_for_period_end_at = models.DateTimeField(null=True, blank=True)
    stripe_checkout_session_id = models.CharField(max_length=128, blank=True, default="", db_index=True)
    stripe_payment_intent_id = models.CharField(max_length=128, blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="queued", db_index=True)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Client Queued Plan Change"
        verbose_name_plural = "Client Queued Plan Changes"

    def __str__(self):
        return f"{self.user.email} | queued {self.target_offer_code} ({self.target_coaching_term})"


class ClientProgressPhoto(models.Model):
    """
    Client body progress photo uploads.
    Rules enforced in API layer:
    - max 1 photo per user per day
    - max 30 photos per user per calendar month
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="progress_photos")
    file = models.FileField(upload_to="client_progress_photos/%Y/%m/")
    captured_for_date = models.DateField(db_index=True)
    same_position = models.BooleanField(default=True)
    same_lighting = models.BooleanField(default=True)
    same_time_of_day = models.BooleanField(default=True)
    notes = models.CharField(max_length=300, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-captured_for_date", "-created_at")
        verbose_name = "Client Progress Photo"
        verbose_name_plural = "Client Progress Photos"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "captured_for_date"],
                name="client_unique_progress_photo_per_day",
            ),
            models.CheckConstraint(
                check=Q(notes__isnull=False),
                name="client_progress_photo_notes_not_null",
            ),
        ]

    def __str__(self):
        return f"{self.user.email} | {self.captured_for_date}"


class ClientWeightEntry(models.Model):
    UNIT_CHOICES = [
        ("lbs", "LBS"),
        ("kg", "KG"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="weight_entries")
    measured_at = models.DateTimeField(db_index=True)
    weight_value = models.DecimalField(max_digits=6, decimal_places=2)
    unit = models.CharField(max_length=8, choices=UNIT_CHOICES, default="lbs")
    notes = models.CharField(max_length=160, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-measured_at", "-created_at")
        verbose_name = "Client Weight Entry"
        verbose_name_plural = "Client Weight Entries"
        constraints = [
            models.CheckConstraint(
                check=Q(weight_value__gt=0),
                name="client_weight_entry_value_positive",
            ),
        ]

    def __str__(self):
        return f"{self.user.email} | {self.weight_value} {self.unit} @ {self.measured_at}"


class DiscountCode(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ("percent", "Percent Off"),
        ("fixed_amount", "Fixed Amount Off"),
    ]
    SCOPE_CHOICES = [
        ("one_time", "One-Time Purchase"),
        ("recurring", "Recurring Subscription"),
        ("either", "Either"),
    ]

    code = models.CharField(max_length=64, unique=True, db_index=True)
    name = models.CharField(max_length=120, blank=True, default="")
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True, db_index=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES, default="percent")
    percent_off = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    amount_cents = models.PositiveIntegerField(default=0)
    scope = models.CharField(max_length=16, choices=SCOPE_CHOICES, default="either")
    eligible_offer_codes = models.JSONField(default=list, blank=True)
    eligible_sale_channels = models.JSONField(default=list, blank=True)
    associated_admin = models.ForeignKey(
        AdminIdentity,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="discount_codes",
    )
    max_redemptions = models.PositiveIntegerField(null=True, blank=True)
    redeemed_count = models.PositiveIntegerField(default=0)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Discount Code"
        verbose_name_plural = "Discount Codes"

    def save(self, *args, **kwargs):
        self.code = (self.code or "").strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.code or "DISCOUNT"


class ClientMealPlanGenerationJob(models.Model):
    DAY_CHOICES = ClientMealComboSelection.DAY_CHOICES
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="meal_plan_generation_jobs")
    client_profile = models.ForeignKey(
        "ClientProfile",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="meal_plan_generation_jobs",
    )
    day_of_week = models.CharField(max_length=12, choices=DAY_CHOICES, db_index=True)
    algorithm_version = models.CharField(max_length=32, default="wp_v1")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="pending", db_index=True)
    total_steps = models.PositiveSmallIntegerField(default=10)
    current_step = models.PositiveSmallIntegerField(default=0)
    progress_percent = models.PositiveSmallIntegerField(default=0)
    input_snapshot_json = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Client Meal Plan Generation Job"
        verbose_name_plural = "Client Meal Plan Generation Jobs"

    def __str__(self):
        return f"{self.user.email} | {self.day_of_week} | {self.status} ({self.progress_percent}%)"


class ClientMealPlanGenerationStep1Row(models.Model):
    job = models.ForeignKey(
        "ClientMealPlanGenerationJob",
        on_delete=models.CASCADE,
        related_name="step1_rows",
    )
    meal_number = models.PositiveSmallIntegerField()
    error_code = models.IntegerField(db_index=True)
    pro_negative = models.DecimalField(max_digits=12, decimal_places=6, default=0)
    carbs_negative = models.DecimalField(max_digits=12, decimal_places=6, default=0)
    fats_negative = models.DecimalField(max_digits=12, decimal_places=6, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("meal_number", "error_code")
        verbose_name = "Client Meal Plan Generation Step1 Row"
        verbose_name_plural = "Client Meal Plan Generation Step1 Rows"
        constraints = [
            models.UniqueConstraint(
                fields=["job", "meal_number", "error_code"],
                name="client_meal_plan_step1_unique_row",
            )
        ]
        indexes = [
            models.Index(fields=["job", "meal_number"], name="client_step1_job_meal_idx"),
        ]

    def __str__(self):
        return f"Job {self.job_id} | meal {self.meal_number} | error {self.error_code}"


class ClientMealPlanGeneratedMeal(models.Model):
    DAY_CHOICES = ClientMealComboSelection.DAY_CHOICES

    job = models.ForeignKey(
        "ClientMealPlanGenerationJob",
        on_delete=models.CASCADE,
        related_name="generated_meals",
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="generated_meal_rows")
    day_of_week = models.CharField(max_length=12, choices=DAY_CHOICES, db_index=True)
    meal_number = models.PositiveSmallIntegerField()
    combo_template = models.ForeignKey(
        "core.MealComboTemplate",
        to_field="combo_id",
        db_column="combo_id",
        on_delete=models.PROTECT,
        related_name="generated_meal_rows",
    )
    error_code = models.IntegerField(default=0)
    protein1_total = models.DecimalField(max_digits=12, decimal_places=6, default=0)
    protein2_total = models.DecimalField(max_digits=12, decimal_places=6, default=0)
    carbs1_total = models.DecimalField(max_digits=12, decimal_places=6, default=0)
    carbs2_total = models.DecimalField(max_digits=12, decimal_places=6, default=0)
    fats1_total = models.DecimalField(max_digits=12, decimal_places=6, default=0)
    fats2_total = models.DecimalField(max_digits=12, decimal_places=6, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("day_of_week", "meal_number")
        verbose_name = "Client Meal Plan Generated Meal"
        verbose_name_plural = "Client Meal Plan Generated Meals"
        constraints = [
            models.UniqueConstraint(
                fields=["job", "day_of_week", "meal_number"],
                name="client_generated_meal_unique_job_day_meal",
            )
        ]

    def __str__(self):
        return f"Job {self.job_id} | {self.day_of_week} meal {self.meal_number}"
