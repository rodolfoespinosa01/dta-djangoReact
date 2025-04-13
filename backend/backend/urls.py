import os
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('adminplans.urls')),
    path('api/users/', include('users.urls')),
]

# ✅ Include test-only routes when testing
if os.environ.get("DJANGO_TEST_MODE") == "true":
    from users.tests.admin.test_admin_urls import test_admin_urls
    from users.tests.superadmin.test_superadmin_urls import test_superadmin_urls

    urlpatterns += [
        path("api/test-admin/", include(test_admin_urls)),
        path("api/test-superadmin/", include(test_superadmin_urls)),
    ]
