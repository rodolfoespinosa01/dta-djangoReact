from django.contrib import admin  # 👉 provides access to django’s admin interface tools
from django.contrib.auth.admin import UserAdmin  # 👉 base admin class for managing users in the admin panel
from core.models import (
    ComboMacroErrorLookup,
    CustomUser,
    FoodLibraryItem,
    MealComboTemplate,
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
        'category',
        'measurement_unit',
        'protein',
        'carbs',
        'fats',
        'is_placeholder',
    )
    list_filter = ('category', 'measurement_unit', 'is_placeholder')
    search_fields = ('name', 'source_food_id')
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

# 👉 summary:
# extends the django admin panel to support the custom user model.
# adds role and subscription status fields to both the user list and detail views.
# makes it easy for superusers to manage user roles and billing states in the admin interface.
