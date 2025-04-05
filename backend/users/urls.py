from django.urls import path
from .views import AdminLoginView

urlpatterns = [
    path('adminlogin/', AdminLoginView.as_view(), name='admin-login'),
]
