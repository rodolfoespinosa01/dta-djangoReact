# tests/admin/auth/test_admin_urls.py
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

test_admin_urls = [
    path("token/refresh/", TokenRefreshView.as_view(), name="test_admin_token_refresh"),
]
