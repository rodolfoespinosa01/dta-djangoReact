from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('admin/', include('users.admin_area.urls')),
    path('superadmin/', include('users.superadmin_area.urls')),
    path('client/', include('users.client_area.urls')),
]
