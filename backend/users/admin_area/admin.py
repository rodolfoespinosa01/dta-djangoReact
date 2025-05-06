from django.contrib import admin
from users.admin_area.models import (
    Plan,
    Profile,
    PendingSignup,
    PasswordResetToken,
    AccountHistory,
    PendingPlanActivation,
)

admin.site.register(Plan)
admin.site.register(Profile)
admin.site.register(AccountHistory)
admin.site.register(PendingPlanActivation)
admin.site.register(PendingSignup)
admin.site.register(PasswordResetToken)
