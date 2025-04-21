from django.urls import path, include
from tests.admin.auth.test_admin_urls import test_admin_urls
from tests.superadmin.test_superadmin_urls import test_superadmin_urls

test_urlpatterns = [
    path("api/test/admin/", include(test_admin_urls)),
    path("api/test/superadmin/", include(test_superadmin_urls)),
]
