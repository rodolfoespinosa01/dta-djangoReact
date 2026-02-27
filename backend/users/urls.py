from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from users.views import unified_stripe_webhook

urlpatterns = [
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('stripe_webhook/', unified_stripe_webhook, name='unified_stripe_webhook'),
    path('admin/', include('users.admin_area.urls')),
    path('superadmin/', include('users.superadmin_area.urls')),
    path('client/', include('users.client_area.urls')),
]
