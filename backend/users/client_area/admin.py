import json

from django.contrib import admin
from django.utils.html import format_html

from .models import (
    ClientFoodPreferenceChangeLog,
    ClientMealPlanGeneratedMeal,
    ClientMealPlanGenerationJob,
    ClientMealPlanGenerationStep1Row,
    ClientMacroAccessLink,
    ClientMealComboSelection,
    ClientPendingSignup,
    ClientProfile,
    ClientQuestionnaireProgress,
    ClientQueuedPlanChange,
)


@admin.register(ClientPendingSignup)
class ClientPendingSignupAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "offer_code",
        "billing_cycle",
        "trial_days",
        "sale_channel",
        "admin",
        "created_at",
    )
    list_filter = ("offer_code", "billing_cycle", "sale_channel", "includes_food_plan", "includes_coaching")
    search_fields = ("email", "token", "admin__admin_email", "admin__subdomain_slug")
    readonly_fields = ("created_at", "registration_link_printed_at")


@admin.register(ClientProfile)
class ClientProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "source_owner",
        "sale_channel",
        "offer_code",
        "billing_cycle",
        "trial_days",
        "is_active",
        "updated_at",
    )
    list_filter = ("offer_code", "billing_cycle", "is_active", "includes_food_plan", "includes_coaching", "sale_channel")
    search_fields = ("user__email", "associated_admin__admin_email", "associated_admin__subdomain_slug")
    readonly_fields = (
        "user",
        "associated_admin",
        "sale_channel",
        "offer_code",
        "billing_cycle",
        "trial_days",
        "amount_cents",
        "includes_food_plan",
        "includes_coaching",
        "coaching_term",
        "coaching_expires_at",
        "stripe_customer_id",
        "stripe_subscription_id",
        "is_active",
        "created_at",
        "updated_at",
        "saved_template_names",
        "weekly_meal_plan_overview",
    )
    list_select_related = ("user", "associated_admin")
    fields = (
        "user",
        "associated_admin",
        "sale_channel",
        "offer_code",
        "billing_cycle",
        "trial_days",
        "amount_cents",
        "includes_food_plan",
        "includes_coaching",
        "coaching_term",
        "coaching_expires_at",
        "stripe_customer_id",
        "stripe_subscription_id",
        "is_active",
        "created_at",
        "updated_at",
        "saved_template_names",
        "weekly_meal_plan_overview",
    )

    def source_owner(self, obj):
        if obj.sale_channel == "dta_direct" or not obj.associated_admin:
            return "DTA"
        return f"{obj.associated_admin.admin_email} ({obj.associated_admin.subdomain_slug or 'no-slug'})"

    source_owner.short_description = "Sold By"

    def saved_template_names(self, obj):
        progress = getattr(obj.user, "questionnaire_progress", None)
        payload = (getattr(progress, "answers_json", None) or {})
        templates = ((payload.get("food_preferences") or {}).get("saved_templates") or [])
        if not isinstance(templates, list) or not templates:
            return "No saved templates"
        names = [str((t or {}).get("name") or "Untitled").strip() for t in templates]
        names = [n for n in names if n]
        return ", ".join(names[:20]) if names else "No saved templates"

    saved_template_names.short_description = "User Saved Templates"

    def weekly_meal_plan_overview(self, obj):
        selections = (
            ClientMealComboSelection.objects.filter(user=obj.user)
            .select_related("combo_template")
            .order_by("day_of_week", "meal_number")
        )
        if not selections:
            return "No meal combo selections saved yet."

        day_order = {
            "sunday": 0,
            "monday": 1,
            "tuesday": 2,
            "wednesday": 3,
            "thursday": 4,
            "friday": 5,
            "saturday": 6,
        }
        grouped = {}
        for row in selections:
            grouped.setdefault(row.day_of_week, []).append(row)

        html = [
            "<div style='max-width:1200px;overflow:auto'>",
            "<table style='width:100%;border-collapse:collapse;min-width:980px'>",
            "<thead><tr>",
            "<th style='text-align:left;padding:8px;border-bottom:1px solid #ddd'>Day</th>",
            "<th style='text-align:left;padding:8px;border-bottom:1px solid #ddd'>Meal #</th>",
            "<th style='text-align:left;padding:8px;border-bottom:1px solid #ddd'>Combo ID</th>",
            "<th style='text-align:left;padding:8px;border-bottom:1px solid #ddd'>Proteins</th>",
            "<th style='text-align:left;padding:8px;border-bottom:1px solid #ddd'>Carbs</th>",
            "<th style='text-align:left;padding:8px;border-bottom:1px solid #ddd'>Fats</th>",
            "</tr></thead><tbody>",
        ]
        for day in sorted(grouped.keys(), key=lambda d: day_order.get(d, 99)):
            for row in grouped[day]:
                c = row.combo_template
                html.extend(
                    [
                        "<tr>",
                        f"<td style='padding:6px 8px;border-bottom:1px solid #f0f0f0'>{day.title()}</td>",
                        f"<td style='padding:6px 8px;border-bottom:1px solid #f0f0f0'>{row.meal_number}</td>",
                        f"<td style='padding:6px 8px;border-bottom:1px solid #f0f0f0'>{c.combo_id}</td>",
                        f"<td style='padding:6px 8px;border-bottom:1px solid #f0f0f0'>{c.protein_slot_1} / {c.protein_slot_2}</td>",
                        f"<td style='padding:6px 8px;border-bottom:1px solid #f0f0f0'>{c.carb_slot_1} / {c.carb_slot_2}</td>",
                        f"<td style='padding:6px 8px;border-bottom:1px solid #f0f0f0'>{c.fat_slot_1} / {c.fat_slot_2}</td>",
                        "</tr>",
                    ]
                )
        html.append("</tbody></table></div>")
        return format_html("".join(html))

    weekly_meal_plan_overview.short_description = "Weekly Meal Plan Combo Overview"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ClientQuestionnaireProgress)
class ClientQuestionnaireProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "source_owner", "status", "current_step", "saved_templates_count", "completed_at", "updated_at")
    list_filter = ("status", "current_step")
    search_fields = ("user__email",)
    readonly_fields = ("created_at", "updated_at", "completed_at", "answers_json", "answers_json_pretty")
    fields = (
        "user",
        "status",
        "current_step",
        "completed_at",
        "created_at",
        "updated_at",
        "answers_json",
        "answers_json_pretty",
    )

    def saved_templates_count(self, obj):
        food_pref = (obj.answers_json or {}).get("food_preferences") or {}
        templates = food_pref.get("saved_templates") or []
        return len(templates) if isinstance(templates, list) else 0

    saved_templates_count.short_description = "Saved Templates"

    def answers_json_pretty(self, obj):
        payload = obj.answers_json or {}
        pretty = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True)
        return format_html("<pre style='max-width:1000px;white-space:pre-wrap'>{}</pre>", pretty)

    answers_json_pretty.short_description = "Answers JSON (Pretty)"

    def source_owner(self, obj):
        profile = getattr(obj.user, "client_profile", None)
        if not profile or profile.sale_channel == "dta_direct" or not profile.associated_admin:
            return "DTA"
        return profile.associated_admin.admin_email

    source_owner.short_description = "Sold By"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ClientMealComboSelection)
class ClientMealComboSelectionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "source_owner",
        "day_of_week",
        "meal_number",
        "combo_template_id",
        "combo_slots_summary",
        "updated_at",
    )
    list_filter = ("day_of_week",)
    search_fields = (
        "user__email",
        "combo_template__combo_id",
        "combo_template__protein_slot_1",
        "combo_template__protein_slot_2",
        "combo_template__carb_slot_1",
        "combo_template__carb_slot_2",
        "combo_template__fat_slot_1",
        "combo_template__fat_slot_2",
    )
    autocomplete_fields = ("user", "combo_template")
    list_select_related = ("user", "combo_template", "user__client_profile__associated_admin")
    readonly_fields = ("user", "day_of_week", "meal_number", "combo_template", "created_at", "updated_at", "combo_slots_summary")
    fields = ("user", "day_of_week", "meal_number", "combo_template", "combo_slots_summary", "created_at", "updated_at")

    def combo_slots_summary(self, obj):
        c = obj.combo_template
        return (
            f"P: {c.protein_slot_1}/{c.protein_slot_2} | "
            f"C: {c.carb_slot_1}/{c.carb_slot_2} | "
            f"F: {c.fat_slot_1}/{c.fat_slot_2}"
        )

    combo_slots_summary.short_description = "Combo Foods"

    def source_owner(self, obj):
        profile = getattr(obj.user, "client_profile", None)
        if not profile or profile.sale_channel == "dta_direct" or not profile.associated_admin:
            return "DTA"
        return profile.associated_admin.admin_email

    source_owner.short_description = "Sold By"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ClientFoodPreferenceChangeLog)
class ClientFoodPreferenceChangeLogAdmin(admin.ModelAdmin):
    list_display = ("user", "source_owner", "created_at", "before_template_count", "after_template_count")
    list_filter = ("created_at",)
    search_fields = ("user__email", "client_profile__associated_admin__admin_email", "client_profile__associated_admin__subdomain_slug")
    list_select_related = ("user", "client_profile", "client_profile__associated_admin")
    readonly_fields = (
        "user",
        "client_profile",
        "source_owner_display",
        "created_at",
        "before_json",
        "after_json",
        "before_json_pretty",
        "after_json_pretty",
    )
    fields = (
        "user",
        "client_profile",
        "source_owner_display",
        "created_at",
        "before_json",
        "before_json_pretty",
        "after_json",
        "after_json_pretty",
    )

    def _template_count(self, payload):
        if not isinstance(payload, dict):
            return 0
        templates = payload.get("saved_templates") or []
        return len(templates) if isinstance(templates, list) else 0

    def before_template_count(self, obj):
        return self._template_count(obj.before_json)

    before_template_count.short_description = "Before Templates"

    def after_template_count(self, obj):
        return self._template_count(obj.after_json)

    after_template_count.short_description = "After Templates"

    def source_owner(self, obj):
        profile = obj.client_profile or getattr(obj.user, "client_profile", None)
        if not profile or profile.sale_channel == "dta_direct" or not profile.associated_admin:
            return "DTA"
        return profile.associated_admin.admin_email

    source_owner.short_description = "Sold By"

    def source_owner_display(self, obj):
        return self.source_owner(obj)

    source_owner_display.short_description = "Sold By"

    def before_json_pretty(self, obj):
        pretty = json.dumps(obj.before_json or {}, indent=2, sort_keys=True, ensure_ascii=True)
        return format_html("<pre style='max-width:1000px;white-space:pre-wrap'>{}</pre>", pretty)

    before_json_pretty.short_description = "Before (Pretty)"

    def after_json_pretty(self, obj):
        pretty = json.dumps(obj.after_json or {}, indent=2, sort_keys=True, ensure_ascii=True)
        return format_html("<pre style='max-width:1000px;white-space:pre-wrap'>{}</pre>", pretty)

    after_json_pretty.short_description = "After (Pretty)"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ClientMacroAccessLink)
class ClientMacroAccessLinkAdmin(admin.ModelAdmin):
    list_display = ("email", "sale_channel", "admin", "questionnaire_status", "questionnaire_current_step", "created_at")
    list_filter = ("questionnaire_status", "sale_channel")
    search_fields = ("email", "token", "admin__admin_email", "admin__subdomain_slug")
    readonly_fields = ("created_at", "last_opened_at", "questionnaire_completed_at")


@admin.register(ClientQueuedPlanChange)
class ClientQueuedPlanChangeAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "source_owner",
        "target_offer_code",
        "target_coaching_term",
        "amount_cents",
        "queued_for_period_end_at",
        "status",
        "created_at",
    )
    list_filter = ("status", "target_offer_code", "target_coaching_term")
    search_fields = ("user__email", "stripe_checkout_session_id", "stripe_payment_intent_id")
    list_select_related = ("user", "client_profile", "client_profile__associated_admin")
    readonly_fields = (
        "user", "client_profile", "target_offer_code", "target_coaching_term", "amount_cents",
        "queued_for_period_end_at", "stripe_checkout_session_id", "stripe_payment_intent_id",
        "status", "notes", "created_at", "updated_at",
    )

    def source_owner(self, obj):
        profile = obj.client_profile or getattr(obj.user, "client_profile", None)
        if not profile or profile.sale_channel == "dta_direct" or not profile.associated_admin:
            return "DTA"
        return profile.associated_admin.admin_email

    source_owner.short_description = "Sold By"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ClientMealPlanGenerationJob)
class ClientMealPlanGenerationJobAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "source_owner",
        "day_of_week",
        "status",
        "current_step",
        "progress_percent",
        "created_at",
        "completed_at",
    )
    list_filter = ("status", "day_of_week", "algorithm_version")
    search_fields = ("user__email", "error_message")
    list_select_related = ("user", "client_profile", "client_profile__associated_admin")
    readonly_fields = (
        "user",
        "client_profile",
        "day_of_week",
        "algorithm_version",
        "status",
        "total_steps",
        "current_step",
        "progress_percent",
        "error_message",
        "input_snapshot_json",
        "input_snapshot_pretty",
        "created_at",
        "started_at",
        "completed_at",
        "updated_at",
    )
    fields = readonly_fields

    def source_owner(self, obj):
        profile = obj.client_profile or getattr(obj.user, "client_profile", None)
        if not profile or profile.sale_channel == "dta_direct" or not profile.associated_admin:
            return "DTA"
        return profile.associated_admin.admin_email

    source_owner.short_description = "Sold By"

    def input_snapshot_pretty(self, obj):
        pretty = json.dumps(obj.input_snapshot_json or {}, indent=2, sort_keys=True, ensure_ascii=True)
        return format_html("<pre style='max-width:1000px;white-space:pre-wrap'>{}</pre>", pretty)

    input_snapshot_pretty.short_description = "Input Snapshot (Pretty)"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ClientMealPlanGenerationStep1Row)
class ClientMealPlanGenerationStep1RowAdmin(admin.ModelAdmin):
    list_display = ("job", "user_email", "meal_number", "error_code", "pro_negative", "carbs_negative", "fats_negative")
    list_filter = ("meal_number", "job__day_of_week")
    search_fields = ("job__user__email", "error_code", "job__id")
    list_select_related = ("job", "job__user")
    readonly_fields = ("job", "meal_number", "error_code", "pro_negative", "carbs_negative", "fats_negative", "created_at")

    def user_email(self, obj):
        return obj.job.user.email

    user_email.short_description = "User"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ClientMealPlanGeneratedMeal)
class ClientMealPlanGeneratedMealAdmin(admin.ModelAdmin):
    list_display = ("job", "user", "day_of_week", "meal_number", "combo_template_id", "error_code", "updated_at")
    list_filter = ("day_of_week",)
    search_fields = ("user__email", "job__id", "combo_template__combo_id")
    readonly_fields = (
        "job",
        "user",
        "day_of_week",
        "meal_number",
        "combo_template",
        "error_code",
        "protein1_total",
        "protein2_total",
        "carbs1_total",
        "carbs2_total",
        "fats1_total",
        "fats2_total",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
