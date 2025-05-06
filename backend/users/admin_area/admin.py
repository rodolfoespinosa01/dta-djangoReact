from django.contrib import admin
from users.admin_area.models import (
    Plan,
    Profile,
    PendingSignup,
    PasswordResetToken,
)

admin.site.register(Plan)
admin.site.register(Profile)
admin.site.register(PendingSignup)
admin.site.register(PasswordResetToken)
