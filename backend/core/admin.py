from django.contrib import admin  # 👉 provides access to django’s admin interface tools
from django.contrib.auth.admin import UserAdmin  # 👉 base admin class for managing users in the admin panel
from core.models import (
    CarbCyclingDefault,
    ComboMacroErrorLookup,
    CustomUser,
    FoodLibraryItem,
    KetoDefault,
    MealComboTemplate,
    ProteinShakeIngredientSlot,
    ProteinShakeTemplate,
    StandardDefault,
    TDEEDefault,
)  # 👉 imports the custom user model to customize how it appears in the admin


class CustomUserAdmin(UserAdmin):  # 👉 extends the default UserAdmin to display and manage custom fields
    model = CustomUser  # 👉 sets the model to use in this admin class

    list_display = ('username', 'email', 'role', 'subscription_status', 'is_active', 'is_staff')
    # 👉 defines which fields are shown in the user list view in the admin panel

    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('role', 'subscription_status')}),
    )
    # 👉 adds custom fields to the user edit form in the admin panel


admin.site.register(CustomUser, CustomUserAdmin)  # 👉 registers the custom user model with the custom admin config


@admin.register(FoodLibraryItem)
class FoodLibraryItemAdmin(admin.ModelAdmin):
    list_display = (
        'source_food_id',
        'name',
        'display_name',
        'macro',
        'category',
        'canonical_category',
        'source_type',
        'approval_status',
        'is_standard',
        'is_active',
        'measurement_unit',
        'preparation_state',
        'measurement_basis_label',
        'protein',
        'carbs',
        'fats',
        'is_placeholder',
    )
    list_filter = ('macro', 'category', 'canonical_category', 'source_type', 'approval_status', 'is_standard', 'is_active', 'measurement_unit', 'preparation_state', 'is_placeholder')
    search_fields = ('name', 'display_name', 'category', 'canonical_category', 'brand_name', 'source_food_id')
    ordering = ('source_food_id',)


@admin.register(MealComboTemplate)
class MealComboTemplateAdmin(admin.ModelAdmin):
    list_display = (
        'combo_id',
        'protein_slot_1',
        'protein_slot_2',
        'carb_slot_1',
        'carb_slot_2',
        'fat_slot_1',
        'fat_slot_2',
    )
    search_fields = (
        'combo_id',
        'protein_slot_1',
        'protein_slot_2',
        'carb_slot_1',
        'carb_slot_2',
        'fat_slot_1',
        'fat_slot_2',
    )
    ordering = ('combo_id',)


@admin.register(ComboMacroErrorLookup)
class ComboMacroErrorLookupAdmin(admin.ModelAdmin):
    list_display = ('error_code', 'protein_error', 'carbs_error', 'fats_error')
    search_fields = ('error_code',)
    ordering = ('error_code',)


class ProteinShakeIngredientSlotInline(admin.TabularInline):
    model = ProteinShakeIngredientSlot
    extra = 0
    autocomplete_fields = ("default_food_library_item",)
    fields = (
        "slot_key",
        "display_name",
        "required",
        "default_food_library_item",
        "default_serving_amount",
        "default_serving_unit",
        "allow_user_override",
        "allow_exclude",
        "macro_role",
        "sort_order",
    )


@admin.register(ProteinShakeTemplate)
class ProteinShakeTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "active", "default_scoop_count", "min_scoop_count", "max_scoop_count", "updated_at")
    list_filter = ("active",)
    search_fields = ("name", "slug", "description")
    readonly_fields = ("created_at", "updated_at")
    prepopulated_fields = {"slug": ("name",)}
    inlines = (ProteinShakeIngredientSlotInline,)


@admin.register(ProteinShakeIngredientSlot)
class ProteinShakeIngredientSlotAdmin(admin.ModelAdmin):
    list_display = ("template", "slot_key", "display_name", "required", "macro_role", "default_food_library_item", "sort_order")
    list_filter = ("slot_key", "required", "macro_role", "template")
    search_fields = ("display_name", "template__name", "default_food_library_item__name", "default_food_library_item__category")
    autocomplete_fields = ("template", "default_food_library_item")


@admin.register(TDEEDefault)
class TDEEDefaultAdmin(admin.ModelAdmin):
    list_display = (
        'version',
        'lose_weight_percent',
        'maintain_weight_percent',
        'gain_weight_percent',
        'updated_at',
    )
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('version',)


@admin.register(StandardDefault)
class StandardDefaultAdmin(admin.ModelAdmin):
    list_display = (
        'version',
        'goal',
        'protein_factor_value',
        'carb_percent',
        'fat_percent',
        'updated_at',
    )
    list_filter = ('version', 'goal')
    search_fields = ('goal',)
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('version', 'created_at')


@admin.register(KetoDefault)
class KetoDefaultAdmin(admin.ModelAdmin):
    list_display = (
        'version',
        'goal',
        'protein_factor_value',
        'carb_percent',
        'fat_percent',
        'updated_at',
    )
    list_filter = ('version', 'goal')
    search_fields = ('goal',)
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('version', 'created_at')


@admin.register(CarbCyclingDefault)
class CarbCyclingDefaultAdmin(admin.ModelAdmin):
    list_display = (
        'version',
        'goal',
        'protein_factor_value',
        'low_day_carb_percent',
        'low_day_fat_percent',
        'high_day_carb_percent',
        'high_day_fat_percent',
        'updated_at',
    )
    list_filter = ('version', 'goal')
    search_fields = ('goal',)
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('version', 'created_at')

# 👉 summary:
# extends the django admin panel to support the custom user model.
# adds role and subscription status fields to both the user list and detail views.
# makes it easy for superusers to manage user roles and billing states in the admin interface.
