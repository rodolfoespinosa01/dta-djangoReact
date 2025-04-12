from django.contrib import admin
from django.urls import path, include
import os

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('adminplans.urls')),
    path('api/users/', include('users.urls')),
]

# ✅ TEST-ONLY ROUTES
if os.environ.get("DJANGO_TEST_MODE") == "true":
    from users import test_admin_urls, test_superadmin_urls

    urlpatterns += [
        path("api/test-admin/", include(test_admin_urls)),
        path("api/test-superadmin/", include(test_superadmin_urls)),
    ]