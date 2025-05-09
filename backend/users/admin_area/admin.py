from django.contrib import admin
from users.admin_area.models import (
    Plan,
    Profile,
    PendingSignup,
    PasswordResetToken,
    AccountHistory,
    PendingPlanActivation,
    PreCheckoutEmail,
    ScheduledSubscription,
)

# Registering models normally
admin.site.register(Plan)
admin.site.register(Profile)
admin.site.register(AccountHistory)
admin.site.register(PendingPlanActivation)
admin.site.register(PendingSignup)
admin.site.register(PasswordResetToken)

@admin.register(PreCheckoutEmail)
class PreCheckoutEmailAdmin(admin.ModelAdmin):
    list_display = ('email', 'created_at')
    readonly_fields = ('created_at',)

@admin.register(ScheduledSubscription)
class ScheduledSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'starts_on', 'created_at']
    list_filter = ['plan']
    search_fields = ['user__email', 'stripe_subscription_id']