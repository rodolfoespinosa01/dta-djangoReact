from django.contrib import admin
from .models import AdminPlan, AdminProfile, AdminPendingSignup
from django.apps import AppConfig


class AdminPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'display_price', 'stripe_price_id')

    def display_price(self, obj):
        return f"${obj.price_cents / 100:.2f}"
    display_price.short_description = 'Price (USD)'

admin.site.register(AdminPlan, AdminPlanAdmin)
admin.site.register(AdminProfile)
admin.site.register(AdminPendingSignup)

class AdminplansConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'adminplans'

    def ready(self):
        import adminplans.signals
