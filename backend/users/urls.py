from django.urls import path

from users.views.superadmin.SuperAdminDashboardView import SuperAdminDashboardView
from users.views.superadmin.SuperAdminLoginView import SuperAdminLoginView

from users.views.admin.AdminDashboardView import AdminDashboardView
from users.views.admin.AdminLoginView import AdminLoginView
from users.views.admin.AdminForgotPasswordView import AdminForgotPasswordView
from users.views.admin.AdminResetPasswordConfirmView import AdminResetPasswordConfirmView


# ✅ Updated: import from tasks
from users.tasks.admin.register_admin import register_admin

from users.tasks.admin.auth_admin import (
    get_pending_admin_signup,
    login_admin,
    cancel_admin_trial_auto_renew
)

urlpatterns = [
    path('superadmin/dashboard/', SuperAdminDashboardView.as_view(), name='superadmin-dashboard'),
    path('superadmin-login/', SuperAdminLoginView.as_view(), name='superadmin-login'),

    path('register-admin/', register_admin),
    path('admin-login/', AdminLoginView.as_view(), name='admin-login'),
    path('admin-dashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),
    path('pending-signup/<str:token>/', get_pending_admin_signup),
    path('admin/forgot-password/', AdminForgotPasswordView.as_view(), name='admin-forgot-password'),
    path('admin/reset-password/confirm/', AdminResetPasswordConfirmView.as_view(), name='admin-reset-password-confirm'),
    path('admin/cancel-auto-renew/', cancel_admin_trial_auto_renew),
]

