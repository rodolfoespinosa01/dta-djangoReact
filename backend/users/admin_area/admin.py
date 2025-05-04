from django.contrib import admin
from users.admin_area.models import (
    AdminPlan,
    AdminProfile,
    AdminPendingSignup,
    AdminPasswordResetToken,
)

from users.admin_area.admin_configs.admin_plan_admin import AdminPlanAdmin

admin.site.register(AdminPlan, AdminPlanAdmin)
admin.site.register(AdminProfile)
admin.site.register(AdminPendingSignup)
admin.site.register(AdminPasswordResetToken)
