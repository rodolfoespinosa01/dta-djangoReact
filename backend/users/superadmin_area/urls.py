from django.urls import path
from users.superadmin_area.views import superadmin_dashboard
from users.superadmin_area.views.superadmin_token_login import SuperAdminTokenObtainPairView

urlpatterns = [
    path('dashboard/', superadmin_dashboard, name='superadmin_dashboard'),
    path('login/', SuperAdminTokenObtainPairView.as_view(), name='superadmin_login'),
]
