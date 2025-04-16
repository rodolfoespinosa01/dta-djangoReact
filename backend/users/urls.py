from django.urls import path

from .views import (
    SuperAdminDashboardView,
    SuperAdminLoginView,
    AdminLoginView,
    AdminDashboardView,
    AdminForgotPasswordView,
    AdminResetPasswordConfirmView
)

# ✅ Updated: import from tasks
from users.tasks.admin.register_admin import register_admin

# 🕒 Pending refactors:
# get_pending_signup and cancel_admin_trial_auto_renew are still in views.py
from .views import get_pending_signup, cancel_admin_trial_auto_renew


urlpatterns = [
    path('superadmin/dashboard/', SuperAdminDashboardView.as_view(), name='superadmin-dashboard'),
    path('superadminlogin/', SuperAdminLoginView.as_view(), name='superadmin-login'),
    
    path('register-admin/', register_admin),
    path('adminlogin/', AdminLoginView.as_view(), name='admin-login'),
    path('admindashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),
    path('pending-signup/<str:token>/', get_pending_signup),
    path('admin/forgot-password/', AdminForgotPasswordView.as_view(), name='admin-forgot-password'),
    path('admin/reset-password/confirm/', AdminResetPasswordConfirmView.as_view(), name='admin-reset-password-confirm'),
    path('admin/cancel-auto-renew/', cancel_admin_trial_auto_renew),
]
