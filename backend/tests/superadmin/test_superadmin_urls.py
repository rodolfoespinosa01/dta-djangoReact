# tests/superadmin/test_superadmin_urls.py
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

test_superadmin_urls = [
    path("token/refresh/", TokenRefreshView.as_view(), name="test_superadmin_token_refresh"),
]
