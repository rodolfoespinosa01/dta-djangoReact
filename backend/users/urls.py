from django.urls import path
from .views import SuperAdminDashboardView, SuperAdminLoginView
from .views import AdminLoginView, AdminDashboardView, AdminForgotPasswordView, AdminResetPasswordConfirmView
from .views import register_admin, get_pending_signup

urlpatterns = [
    path('superadmin/dashboard/', SuperAdminDashboardView.as_view(), name='superadmin-dashboard'),
    path('superadminlogin/', SuperAdminLoginView.as_view(), name='superadmin-login'),
    
    path('register-admin/', register_admin),
    path('adminlogin/', AdminLoginView.as_view(), name='admin-login'),
    path('admindashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),
    path('pending-signup/<str:token>/', get_pending_signup),
    path('admin/forgot-password/', AdminForgotPasswordView.as_view(), name='admin-forgot-password'),
    path('admin/reset-password/confirm/', AdminResetPasswordConfirmView.as_view(), name='admin-reset-password-confirm'),
]
