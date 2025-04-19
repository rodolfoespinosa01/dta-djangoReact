# backend/tests/test_urls.py

from django.urls import path, include

# 🧪 Test routes per role
from tests.admin.auth.test_admin_urls import test_admin_urls
from tests.superadmin.test_superadmin_urls import test_superadmin_urls
# from tests.client.test_client_urls import test_client_urls

# 🚀 Combine all test routes into one export
test_urlpatterns = [
    path("api/test-admin/", include(test_admin_urls)),
    path("api/test-superadmin/", include(test_superadmin_urls)),
    # path("api/test-client/", include(test_client_urls)),  # safe even if empty
]
