import json

from django.contrib import admin
from django.template.response import TemplateResponse
from django.urls import path
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
    AdminParameterSettings,
    AdminParameterSettingsChangeLog,
)
from users.admin_area.configs.admin_parameter_defaults import get_admin_parameter_defaults_v1

# ✅ Core admin models
admin.site.register(Plan)
admin.site.register(Profile)
admin.site.register(PasswordResetToken)
admin.site.register(PreCheckout)
admin.site.register(TransactionLog)


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


@admin.register(AdminParameterSettings)
class AdminParameterSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "admin_email",
        "initialized",
        "defaults_version_applied",
        "updated_at",
        "created_at",
    )
    list_filter = ("initialized", "defaults_version_applied", "updated_at", "created_at")
    search_fields = ("admin__admin_email", "admin__adminID")
    readonly_fields = ("created_at", "updated_at", "parameters_json_pretty")
    autocomplete_fields = ("admin",)
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "admin",
                    "initialized",
                    "defaults_version_applied",
                    "created_at",
                    "updated_at",
                )
            },
        ),
        ("Parameters (JSON)", {"fields": ("parameters_json",)}),
        ("Pretty View (Read-only)", {"fields": ("parameters_json_pretty",)}),
    )

    def admin_email(self, obj):
        return obj.admin.admin_email

    admin_email.short_description = "Admin Email"
    admin_email.admin_order_field = "admin__admin_email"

    def parameters_json_pretty(self, obj):
        pretty = json.dumps(obj.parameters_json, indent=2)
        return format_html(
            '<pre style="max-height:520px; overflow:auto; background:#111827; color:#e5e7eb; padding:12px; border-radius:8px;">{}</pre>',
            pretty,
        )

    parameters_json_pretty.short_description = "Formatted JSON"


@admin.register(AdminParameterSettingsChangeLog)
class AdminParameterSettingsChangeLogAdmin(admin.ModelAdmin):
    list_display = ("admin_email", "action", "changed_paths_count", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("admin__admin_email",)
    readonly_fields = (
        "admin",
        "parameter_settings",
        "action",
        "changed_paths_pretty",
        "before_json_pretty",
        "after_json_pretty",
        "created_at",
    )
    autocomplete_fields = ("admin", "parameter_settings")
    fieldsets = (
        (None, {"fields": ("admin", "parameter_settings", "action", "created_at")}),
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
        pretty = json.dumps(obj.changed_paths or [], indent=2)
        return format_html(
            '<pre style="max-height:240px; overflow:auto; background:#111827; color:#e5e7eb; padding:12px; border-radius:8px;">{}</pre>',
            pretty,
        )

    changed_paths_pretty.short_description = "Changed Paths"

    def before_json_pretty(self, obj):
        pretty = json.dumps(obj.before_json, indent=2)
        return format_html(
            '<pre style="max-height:360px; overflow:auto; background:#111827; color:#e5e7eb; padding:12px; border-radius:8px;">{}</pre>',
            pretty,
        )

    before_json_pretty.short_description = "Before"

    def after_json_pretty(self, obj):
        pretty = json.dumps(obj.after_json, indent=2)
        return format_html(
            '<pre style="max-height:360px; overflow:auto; background:#111827; color:#e5e7eb; padding:12px; border-radius:8px;">{}</pre>',
            pretty,
        )

    after_json_pretty.short_description = "After"


def admin_parameter_defaults_view(request):
    defaults = get_admin_parameter_defaults_v1()
    meal_plans = defaults.get("meal_plans", {})
    context = {
        **admin.site.each_context(request),
        "title": "Admin Parameter Defaults (DTA v1)",
        "defaults_version": defaults.get("version", "unknown"),
        "global_defaults_json": json.dumps(
            {
                "version": defaults.get("version"),
                "goal_calorie_adjustments": defaults.get("goal_calorie_adjustments", {}),
                "tdee": defaults.get("tdee", {}),
            },
            indent=2,
        ),
        "standard_defaults_json": json.dumps(meal_plans.get("standard", {}), indent=2),
        "keto_defaults_json": json.dumps(meal_plans.get("keto", {}), indent=2),
        "carb_cycling_defaults_json": json.dumps(meal_plans.get("carb_cycling", {}), indent=2),
        "full_defaults_json": json.dumps(defaults, indent=2),
    }
    return TemplateResponse(
        request,
        "admin/users_admin_area/admin_parameter_defaults.html",
        context,
    )


def _custom_admin_urls():
    return [
        path(
            "users/admin-parameter-defaults/",
            admin.site.admin_view(admin_parameter_defaults_view),
            name="users_admin_parameter_defaults",
        ),
    ]


if not hasattr(admin.site, "_dta_original_get_urls"):
    admin.site._dta_original_get_urls = admin.site.get_urls

    def _get_urls():
        return _custom_admin_urls() + admin.site._dta_original_get_urls()

    admin.site.get_urls = _get_urls
