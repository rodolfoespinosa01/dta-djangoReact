from django.urls import path

# SuperAdmin Views
from users.views.superadmin.superadmin_dashboard import superadmin_dashboard
from users.views.superadmin.superadmin_token_login import SuperAdminTokenObtainPairView

# Admin Views
from users.views.admin.admin_dashboard import AdminDashboardView
from users.views.admin.admin_forgot_password import AdminForgotPasswordView
from users.views.admin.admin_reset_password_confirm import AdminResetPasswordConfirmView
from users.views.admin.admin_login import AdminLoginView

# Admin Tasks (logic outside DRF views)
from users.tasks.admin.admin_register import register_admin
from users.tasks.admin.admin_get_pending_signup import get_pending_admin_signup
from users.tasks.admin.admin_cancel_subscription import cancel_admin_subscription

urlpatterns = [
    # SuperAdmin
    path('superadmin/dashboard/', superadmin_dashboard, name='superadmin_dashboard'),
    path('superadmin_login/', SuperAdminTokenObtainPairView.as_view(), name='superadmin_login'),

    # Admin Auth & Dashboard
    path('admin_login/', AdminLoginView.as_view(), name='admin_login'),
    path('admin-dashboard/', AdminDashboardView.as_view(), name='admin_dashboard'),

    # Admin Registration
    path('register-admin/', register_admin, name='register_admin'),
    path('pending-signup/<str:token>/', get_pending_admin_signup),

    # Admin Password Reset
    path('admin/forgot_password/', AdminForgotPasswordView.as_view(), name='admin_forgot_password'),
    path('admin/reset_password/confirm/', AdminResetPasswordConfirmView.as_view(), name='admin_reset-password-confirm'),

    # Admin Subscription Cancel
    path('admin/cancel_auto_renew/', cancel_admin_subscription),
]
