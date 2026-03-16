import json

from django.contrib import admin
from django.utils.html import format_html
from users.admin_area.models import (
    Plan,
    Profile,
    PendingSignup,
    PasswordResetToken,
    PreCheckout,
    TransactionLog,
    AdminIdentity,
    EventTracker,
    AdminAccountHistory,
    AdminParameterSettingsChangeLog,
    AdminTDEESettings,
    AdminStandardSettings,
    AdminKetoSettings,
    AdminCarbCyclingSettings,
)

# ✅ Core admin models
admin.site.register(Plan)
admin.site.register(Profile)
admin.site.register(PasswordResetToken)
admin.site.register(PreCheckout)
admin.site.register(TransactionLog)


def _pretty_json(value, *, max_height=360):
    pretty = json.dumps(value, indent=2)
    return format_html(
        '<pre style="max-height:{}px; overflow:auto; background:#111827; color:#e5e7eb; padding:12px; border-radius:8px;">{}</pre>',
        max_height,
        pretty,
    )
@admin.register(EventTracker)
class EventTrackerAdmin(admin.ModelAdmin):
    list_display = ('admin_id_column', 'event_type', 'timestamp')
    list_filter = ('event_type', 'timestamp')
    search_fields = ('admin__admin_email', 'event_type', 'details')
    readonly_fields = ('admin_id_display', 'admin_email_display', 'timestamp')

    fieldsets = (
        (None, {
            'fields': ('admin_id_display', 'admin_email_display', 'event_type', 'details', 'timestamp')
        }),
    )

    def admin_id_column(self, obj):
        return str(obj.admin.id)
    admin_id_column.short_description = 'Admin ID'
    admin_id_column.admin_order_field = 'id'

    def admin_id_display(self, obj):
        return obj.admin.id
    admin_id_display.short_description = "Admin ID"

    def admin_email_display(self, obj):
        return obj.admin.admin_email
    admin_email_display.short_description = "Admin Email"



# 🕒 Pending Signup
@admin.register(PendingSignup)

class PendingSignupAdmin(admin.ModelAdmin):
    readonly_fields = ('created_at',)
    fields = (
        'email',
        'session_id',
        'token',
        'plan',
        'stripe_transaction_id',
        'is_trial',
        'created_at',
    )
    list_display = ('email', 'plan', 'is_trial', 'created_at')


@admin.register(AdminIdentity)
class AdminIdentityAdmin(admin.ModelAdmin):
    list_display = ('id', 'admin_email', 'subdomain_slug', 'subdomain_locked_at', 'adminID', 'created_at')
    search_fields = ('admin_email',)
    ordering = ('-created_at',)

    readonly_fields = ('id', 'adminID', 'admin_email', 'subdomain_slug', 'subdomain_locked_at', 'created_at')
    fields = ('id', 'adminID', 'admin_email', 'subdomain_slug', 'subdomain_locked_at', 'created_at')


@admin.register(AdminAccountHistory)
class AdminAccountHistoryAdmin(admin.ModelAdmin):
    list_display = ("admin_email", "event_type", "occurred_at")
    list_filter = ("event_type", "occurred_at")
    search_fields = ("admin__admin_email", "event_type", "details")
    readonly_fields = ("admin", "source_event", "event_type", "details", "metadata", "occurred_at")

    def admin_email(self, obj):
        return obj.admin.admin_email

    admin_email.short_description = "Admin Email"


@admin.register(AdminTDEESettings)
class AdminTDEESettingsAdmin(admin.ModelAdmin):
    list_display = (
        "admin_email",
        "initialized",
        "defaults_version_applied",
        "lose_weight_percent",
        "maintain_weight_percent",
        "gain_weight_percent",
        "updated_at",
    )
    list_filter = ("initialized", "defaults_version_applied", "updated_at")
    search_fields = ("admin__admin_email",)
    autocomplete_fields = ("admin",)
    readonly_fields = (
        "created_at",
        "updated_at",
        "category_multipliers_pretty",
        "category_mapping_pretty",
        "weekly_splits_pretty",
    )
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "admin",
                    "initialized",
                    "defaults_version_applied",
                    "lose_weight_percent",
                    "maintain_weight_percent",
                    "gain_weight_percent",
                    "created_at",
                    "updated_at",
                )
            },
        ),
        ("TDEE JSON", {"fields": (
            "category_multipliers_json",
            "category_mapping_by_lifestyle_and_training_days_json",
            "weekly_day_multiplier_splits_json",
        )}),
        ("Pretty View (Read-only)", {"fields": (
            "category_multipliers_pretty",
            "category_mapping_pretty",
            "weekly_splits_pretty",
        )}),
    )

    def admin_email(self, obj):
        return obj.admin.admin_email

    admin_email.short_description = "Admin Email"
    admin_email.admin_order_field = "admin__admin_email"

    def category_multipliers_pretty(self, obj):
        return _pretty_json(obj.category_multipliers_json, max_height=180)

    category_multipliers_pretty.short_description = "Category Multipliers"

    def category_mapping_pretty(self, obj):
        return _pretty_json(obj.category_mapping_by_lifestyle_and_training_days_json, max_height=220)

    category_mapping_pretty.short_description = "Lifestyle / Training Day Mapping"

    def weekly_splits_pretty(self, obj):
        return _pretty_json(obj.weekly_day_multiplier_splits_json, max_height=320)

    weekly_splits_pretty.short_description = "Weekly Day Multiplier Splits"


class _AdminMacroSettingsBase(admin.ModelAdmin):
    readonly_fields = ("created_at", "updated_at", "meal_macro_distribution_pretty")
    autocomplete_fields = ("admin",)

    def admin_email(self, obj):
        return obj.admin.admin_email

    admin_email.short_description = "Admin Email"
    admin_email.admin_order_field = "admin__admin_email"

    def meal_macro_distribution_pretty(self, obj):
        return _pretty_json(obj.meal_macro_distribution_json, max_height=360)

    meal_macro_distribution_pretty.short_description = "Meal Macro Distribution"


@admin.register(AdminStandardSettings)
class AdminStandardSettingsAdmin(_AdminMacroSettingsBase):
    list_display = (
        "admin_email",
        "goal",
        "defaults_version_applied",
        "protein_factor_value",
        "carb_percent",
        "fat_percent",
        "updated_at",
    )
    list_filter = ("goal", "defaults_version_applied", "updated_at")
    search_fields = ("admin__admin_email", "goal")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "admin",
                    "goal",
                    "defaults_version_applied",
                    "protein_factor_unit",
                    "protein_factor_value",
                    "carb_percent",
                    "fat_percent",
                    "created_at",
                    "updated_at",
                )
            },
        ),
        ("Meal Macro Distribution", {"fields": ("meal_macro_distribution_json",)}),
        ("Pretty View (Read-only)", {"fields": ("meal_macro_distribution_pretty",)}),
    )


@admin.register(AdminKetoSettings)
class AdminKetoSettingsAdmin(_AdminMacroSettingsBase):
    list_display = (
        "admin_email",
        "goal",
        "defaults_version_applied",
        "protein_factor_value",
        "carb_percent",
        "fat_percent",
        "updated_at",
    )
    list_filter = ("goal", "defaults_version_applied", "updated_at")
    search_fields = ("admin__admin_email", "goal")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "admin",
                    "goal",
                    "defaults_version_applied",
                    "protein_factor_unit",
                    "protein_factor_value",
                    "carb_percent",
                    "fat_percent",
                    "created_at",
                    "updated_at",
                )
            },
        ),
        ("Meal Macro Distribution", {"fields": ("meal_macro_distribution_json",)}),
        ("Pretty View (Read-only)", {"fields": ("meal_macro_distribution_pretty",)}),
    )


@admin.register(AdminCarbCyclingSettings)
class AdminCarbCyclingSettingsAdmin(_AdminMacroSettingsBase):
    list_display = (
        "admin_email",
        "goal",
        "defaults_version_applied",
        "protein_factor_value",
        "low_day_carb_percent",
        "low_day_fat_percent",
        "high_day_carb_percent",
        "high_day_fat_percent",
        "updated_at",
    )
    list_filter = ("goal", "defaults_version_applied", "updated_at")
    search_fields = ("admin__admin_email", "goal")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "admin",
                    "goal",
                    "defaults_version_applied",
                    "protein_factor_unit",
                    "protein_factor_value",
                    "low_day_carb_percent",
                    "low_day_fat_percent",
                    "high_day_carb_percent",
                    "high_day_fat_percent",
                    "created_at",
                    "updated_at",
                )
            },
        ),
        ("Meal Macro Distribution", {"fields": ("meal_macro_distribution_json",)}),
        ("Pretty View (Read-only)", {"fields": ("meal_macro_distribution_pretty",)}),
    )


@admin.register(AdminParameterSettingsChangeLog)
class AdminParameterSettingsChangeLogAdmin(admin.ModelAdmin):
    list_display = ("admin_email", "action", "changed_paths_count", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("admin__admin_email",)
    readonly_fields = (
        "admin",
        "action",
        "changed_paths_pretty",
        "before_json_pretty",
        "after_json_pretty",
        "created_at",
    )
    autocomplete_fields = ("admin",)
    fieldsets = (
        (None, {"fields": ("admin", "action", "created_at")}),
        ("Changed Paths", {"fields": ("changed_paths_pretty",)}),
        ("Before", {"fields": ("before_json_pretty",)}),
        ("After", {"fields": ("after_json_pretty",)}),
    )

    def admin_email(self, obj):
        return obj.admin.admin_email

    admin_email.short_description = "Admin Email"
    admin_email.admin_order_field = "admin__admin_email"

    def changed_paths_count(self, obj):
        return len(obj.changed_paths or [])

    changed_paths_count.short_description = "Changed Paths"

    def changed_paths_pretty(self, obj):
        return _pretty_json(obj.changed_paths or [], max_height=240)

    changed_paths_pretty.short_description = "Changed Paths"

    def before_json_pretty(self, obj):
        return _pretty_json(obj.before_json, max_height=360)

    before_json_pretty.short_description = "Before"

    def after_json_pretty(self, obj):
        return _pretty_json(obj.after_json, max_height=360)

    after_json_pretty.short_description = "After"
