from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from core.models import CustomUser

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('username', 'email', 'role', 'subscription_status', 'is_active', 'is_staff')

    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('role', 'subscription_status')}),
    )

admin.site.register(CustomUser, CustomUserAdmin)
