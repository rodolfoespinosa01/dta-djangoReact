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

# ✅ Register core models with default admin interface
admin.site.register(Plan)  # 👉 admin plans: trial, monthly, etc.
admin.site.register(Profile) # 👉 subscription snapshots per admin
admin.site.register(AccountHistory) # 👉 lifecycle event history (signup, cancel, etc.)
admin.site.register(PendingPlanActivation) # 👉 holds scheduled reactivations
admin.site.register(PendingSignup) # 👉 stores post-checkout, pre-registration data
admin.site.register(PasswordResetToken) # 👉 holds tokens for password resets


# 📩 custom admin for viewing pre-checkout email captures
@admin.register(PreCheckoutEmail)
class PreCheckoutEmailAdmin(admin.ModelAdmin):
    list_display = ('email', 'created_at')  # 👉 show email and timestamp
    readonly_fields = ('created_at',) # 🔒 prevent editing creation date


# 📅 custom admin for reviewing scheduled subscriptions
@admin.register(ScheduledSubscription)
class ScheduledSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'starts_on', 'created_at']  # 👉 columns to display
    list_filter = ['plan']  # 👉 filter by plan type
    search_fields = ['user__email', 'stripe_subscription_id']  # 🔍 search by user or stripe ID


# 👉 summary:
# registers all admin subscription-related models to the Django admin site.
# includes custom display options for PreCheckoutEmail and ScheduledSubscription.
# used by platform owners to monitor billing events, signups, reactivations, and access lifecycle.