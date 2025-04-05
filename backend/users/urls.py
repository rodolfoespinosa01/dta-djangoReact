from django.urls import path
from .views import SuperAdminDashboardView, SuperAdminLoginView
from .views import AdminLoginView, AdminDashboardView
from .views import register_admin

urlpatterns = [
    path('superadmin/dashboard/', SuperAdminDashboardView.as_view(), name='superadmin-dashboard'),
    path('superadminlogin/', SuperAdminLoginView.as_view(), name='superadmin-login'),
    
    path('register-admin/', register_admin),
    path('adminlogin/', AdminLoginView.as_view(), name='admin-login'),
    path('admindashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),
]
