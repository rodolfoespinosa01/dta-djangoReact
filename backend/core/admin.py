from django.contrib import admin  # 👉 provides access to django’s admin interface tools
from django.contrib.auth.admin import UserAdmin  # 👉 base admin class for managing users in the admin panel
from core.models import CustomUser  # 👉 imports the custom user model to customize how it appears in the admin


class CustomUserAdmin(UserAdmin):  # 👉 extends the default UserAdmin to display and manage custom fields
    model = CustomUser  # 👉 sets the model to use in this admin class

    list_display = ('username', 'email', 'role', 'subscription_status', 'is_active', 'is_staff')
    # 👉 defines which fields are shown in the user list view in the admin panel

    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('role', 'subscription_status')}),
    )
    # 👉 adds custom fields to the user edit form in the admin panel


admin.site.register(CustomUser, CustomUserAdmin)  # 👉 registers the custom user model with the custom admin config

# 👉 summary:
# extends the django admin panel to support the custom user model.
# adds role and subscription status fields to both the user list and detail views.
# makes it easy for superusers to manage user roles and billing states in the admin interface.