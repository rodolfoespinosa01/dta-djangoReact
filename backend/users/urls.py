from django.urls import path
from .views import AdminLoginView
from .views import AdminDashboardView

urlpatterns = [
    path('adminlogin/', AdminLoginView.as_view(), name='admin-login'),
    path('admindashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),
]
