from django.urls import path

from users.views.superadmin.superadmin_dashboard import superadmin_dashboard
from users.views.superadmin.superadmin_token_login import SuperAdminTokenObtainPairView

from users.views.admin.admin_dashboard import AdminDashboardView
from users.views.admin.admin_login import AdminLoginView
from users.views.admin.admin_forgot_password import AdminForgotPasswordView
from users.views.admin.admin_reset_password_confirm import AdminResetPasswordConfirmView
from users.views.admin.admin_token_login import AdminTokenObtainPairView

from users.tasks.admin.admin_register import register_admin
from users.tasks.admin.admin_login import login_admin
from users.tasks.admin.admin_get_pending_signup import get_pending_admin_signup
from users.tasks.admin.admin_cancel_subscription import cancel_admin_subscription

urlpatterns = [
    path('superadmin/dashboard/', superadmin_dashboard, name='superadmin-dashboard'),
    path('superadmin-login/', SuperAdminTokenObtainPairView.as_view(), name='superadmin-login'),

    path('register-admin/', register_admin),
    path('admin-login/', AdminLoginView.as_view(), name='admin-login'),
    path('admin-dashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),
    path('pending-signup/<str:token>/', get_pending_admin_signup),
    path('admin/forgot-password/', AdminForgotPasswordView.as_view(), name='admin-forgot-password'),
    path('admin/reset-password/confirm/', AdminResetPasswordConfirmView.as_view(), name='admin-reset-password-confirm'),
    path('admin-login/', AdminTokenObtainPairView.as_view(), name='admin-login'),
]

