from django.contrib import admin
from users.admin_area.models import (
    Plan,
    Profile,
    PendingSignup,
    PasswordResetToken,
    AccountHistory,
    PreCheckoutEmail,
    TransactionLog
)

# ✅ Register core models with default admin interface
admin.site.register(Plan)  # 👉 admin plans: trial, monthly, etc.
admin.site.register(Profile) # 👉 subscription snapshots per admin
admin.site.register(AccountHistory) # 👉 lifecycle event history (signup, cancel, etc.)

# PENDING SIGNUP
@admin.register(PendingSignup)
class PendingSignupAdmin(admin.ModelAdmin):
    readonly_fields = ('created_at',)
    fields = (
        'email',
        'session_id',
        'token',
        'plan',
        'stripe_transaction_id',
        'is_trial',
        'created_at',
    )
    list_display = ('email', 'plan', 'is_trial', 'created_at')
    
admin.site.register(PasswordResetToken) # 👉 holds tokens for password resets
admin.site.register(TransactionLog) # 👉 transaction log
admin.site.register(PreCheckoutEmail)


# 👉 summary:
# registers all admin subscription-related models to the Django admin site.
# includes custom display options for PreCheckoutEmail and ScheduledSubscription.
# used by platform owners to monitor billing events, signups, and access lifecycle.