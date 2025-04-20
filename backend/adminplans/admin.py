from django.contrib import admin
from .models import AdminPlan, AdminProfile, PendingAdminSignup
from django.apps import AppConfig
from .models import AdminAccountHistory



class AdminPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'display_price', 'stripe_price_id')

    def display_price(self, obj):
        return f"${obj.price_cents / 100:.2f}"
    display_price.short_description = 'Price (USD)'

admin.site.register(AdminPlan, AdminPlanAdmin)
admin.site.register(AdminProfile)
admin.site.register(PendingAdminSignup)

class AdminplansConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'adminplans'

    def ready(self):
        import adminplans.signals

class AdminAccountHistoryAdmin(admin.ModelAdmin):
    list_display = ('admin', 'plan_name', 'start_date', 'end_date', 'was_canceled', 'timestamp')

admin.site.register(AdminAccountHistory, AdminAccountHistoryAdmin)

