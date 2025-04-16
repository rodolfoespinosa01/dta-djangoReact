import os
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('adminplans.urls')),
    path('api/users/', include('users.urls')),
]

# 🧪 Only include test routes if DJANGO_TEST_MODE is enabled
if os.environ.get("DJANGO_TEST_MODE") == "true":
    from tests.test_urls import test_urlpatterns
    urlpatterns += test_urlpatterns