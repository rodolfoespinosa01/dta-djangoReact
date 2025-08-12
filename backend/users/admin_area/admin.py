from django.contrib import admin
from users.admin_area.models import (
    Plan,
    Profile,
    PendingSignup,
    PasswordResetToken,
    PreCheckout,
    TransactionLog,
    AdminIdentity,
    EventTracker
)

# ✅ Core admin models
admin.site.register(Plan)
admin.site.register(Profile)
admin.site.register(PasswordResetToken)
admin.site.register(PreCheckout)
admin.site.register(TransactionLog)

@admin.register(EventTracker)
class EventTrackerAdmin(admin.ModelAdmin):
    list_display = ('admin_id_column', 'event_type', 'timestamp')
    list_filter = ('event_type', 'timestamp')
    search_fields = ('admin__admin_email', 'event_type', 'details')
    readonly_fields = ('admin_id_display', 'admin_email_display', 'timestamp')

    fieldsets = (
        (None, {
            'fields': ('admin_id_display', 'admin_email_display', 'event_type', 'details', 'timestamp')
        }),
    )

    def admin_id_column(self, obj):
        return str(obj.admin.id)
    admin_id_column.short_description = 'Admin ID'
    admin_id_column.admin_order_field = 'id'

    def admin_id_display(self, obj):
        return obj.admin.id
    admin_id_display.short_description = "Admin ID"

    def admin_email_display(self, obj):
        return obj.admin.admin_email
    admin_email_display.short_description = "Admin Email"



# 🕒 Pending Signup
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


@admin.register(AdminIdentity)
class AdminIdentityAdmin(admin.ModelAdmin):
    list_display = ('id', 'admin_email', 'adminID', 'created_at')
    search_fields = ('admin_email',)
    ordering = ('-created_at',)

    readonly_fields = ('id', 'adminID', 'admin_email', 'created_at')
    fields = ('id', 'adminID', 'admin_email', 'created_at')

