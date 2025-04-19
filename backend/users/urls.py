from django.urls import path

# SuperAdmin Views
from users.views.superadmin.superadmin_dashboard import superadmin_dashboard
from users.views.superadmin.superadmin_token_login import SuperAdminTokenObtainPairView

# Admin Views
from users.views.admin.admin_dashboard import AdminDashboardView
from users.views.admin.admin_forgot_password import AdminForgotPasswordView
from users.views.admin.admin_reset_password_confirm import AdminResetPasswordConfirmView
from users.views.admin.admin_token_login import AdminTokenObtainPairView as AdminTokenLoginView

# Admin Tasks (logic outside DRF views)
from users.tasks.admin.admin_register import register_admin
from users.tasks.admin.admin_get_pending_signup import get_pending_admin_signup
from users.tasks.admin.admin_cancel_subscription import cancel_admin_subscription

urlpatterns = [
    # SuperAdmin
    path('superadmin/dashboard/', superadmin_dashboard, name='superadmin-dashboard'),
    path('superadmin-login/', SuperAdminTokenObtainPairView.as_view(), name='superadmin-login'),

    # Admin Auth & Dashboard
    path('admin-login/', AdminTokenLoginView.as_view(), name='admin-login'),
    path('admin-dashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),

    # Admin Registration
    path('register-admin/', register_admin, name='register_admin'),
    path('pending-signup/<str:token>/', get_pending_admin_signup),

    # Admin Password Reset
    path('admin/forgot-password/', AdminForgotPasswordView.as_view(), name='admin-forgot-password'),
    path('admin/reset-password/confirm/', AdminResetPasswordConfirmView.as_view(), name='admin-reset-password-confirm'),

    # Admin Subscription Cancel
    path('admin/cancel-auto-renew/', cancel_admin_subscription),
]
