from django.urls import path

# SuperAdmin Views
from users.views.superadmin.superadmin_dashboard import superadmin_dashboard
from users.views.superadmin.superadmin_token_login import SuperAdminTokenObtainPairView

# Admin Views
from users.views.admin.admin_get_pending_signup import admin_get_pending_signup
from users.views.admin.admin_forgot_password import AdminForgotPasswordView
from users.views.admin.admin_reset_password_confirm import AdminResetPasswordConfirmView
from users.views.admin.admin_login import AdminLoginView

# Admin Tasks (still in users)
from users.tasks.admin.admin_register import admin_register

urlpatterns = [
    # SuperAdmin
    path('superadmin/dashboard/', superadmin_dashboard, name='superadmin_dashboard'),
    path('superadmin_login/', SuperAdminTokenObtainPairView.as_view(), name='superadmin_login'),

    # Admin Auth & Registration
    path('admin_login/', AdminLoginView.as_view(), name='admin_login'),
    path('admin_register/', admin_register, name='admin_register'),

    # Admin Password Reset
    path('admin/forgot_password/', AdminForgotPasswordView.as_view(), name='admin_forgot_password'),
    path('admin/reset_password/confirm/', AdminResetPasswordConfirmView.as_view(), name='admin_reset_password_confirm'),

    # Admin Signup Token Lookup
    path('admin_pending_signup/<str:token>/', admin_get_pending_signup, name='admin_get_pending_signup'),
]
