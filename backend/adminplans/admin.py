from django.contrib import admin
from adminplans.models import (
    AdminPlan,
    AdminProfile,
    AdminPendingSignup,
    AdminAccountHistory,
)

# --- AdminPlan ---
class AdminPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'display_price', 'stripe_price_id')

    def display_price(self, obj):
        return f"${obj.price_cents / 100:.2f}"
    display_price.short_description = 'Price (USD)'

admin.site.register(AdminPlan, AdminPlanAdmin)

# --- AdminProfile ---
admin.site.register(AdminProfile)

# --- AdminPendingSignup ---
admin.site.register(AdminPendingSignup)

# --- AdminAccountHistory ---
class AdminAccountHistoryAdmin(admin.ModelAdmin):
    list_display = ('admin', 'plan_name', 'start_date', 'end_date', 'was_canceled', 'timestamp')

admin.site.register(AdminAccountHistory, AdminAccountHistoryAdmin)
