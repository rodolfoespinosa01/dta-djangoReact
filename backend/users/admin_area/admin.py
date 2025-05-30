from django.contrib import admin
from users.admin_area.models import (
    Plan,
    Profile,
    PendingSignup,
    PasswordResetToken,
    AccountHistory,
    PreCheckoutEmail
)

# ✅ Register core models with default admin interface
admin.site.register(Plan)  # 👉 admin plans: trial, monthly, etc.
admin.site.register(Profile) # 👉 subscription snapshots per admin
admin.site.register(AccountHistory) # 👉 lifecycle event history (signup, cancel, etc.)
admin.site.register(PendingSignup) # 👉 stores post-checkout, pre-registration data
admin.site.register(PasswordResetToken) # 👉 holds tokens for password resets


# 📩 custom admin for viewing pre-checkout email captures
@admin.register(PreCheckoutEmail)
class PreCheckoutEmailAdmin(admin.ModelAdmin):
    list_display = ('email', 'created_at')  # 👉 show email and timestamp
    readonly_fields = ('created_at',) # 🔒 prevent editing creation date



# 👉 summary:
# registers all admin subscription-related models to the Django admin site.
# includes custom display options for PreCheckoutEmail and ScheduledSubscription.
# used by platform owners to monitor billing events, signups, and access lifecycle.