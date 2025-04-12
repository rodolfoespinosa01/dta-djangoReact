from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('adminplans.urls')),
    path('api/users/', include('users.urls')),
]

# 🧪 Include test-only routes when running tests
import sys
if "test" in sys.argv:
    urlpatterns += [
        path("api/test-admin/", include("users.test_admin_urls")),
    ]