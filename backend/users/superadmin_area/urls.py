from django.urls import path
from users.superadmin_area.views import dashboard
from users.superadmin_area.views.analytics import analytics
from users.superadmin_area.views.token_login import SuperAdminTokenObtainPairView

urlpatterns = [
    path('dashboard/', dashboard, name='dashboard'),
    path('analytics/', analytics, name='analytics'),
    path('login/', SuperAdminTokenObtainPairView.as_view(), name='login'),
]
