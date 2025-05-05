import os
from django.contrib import admin
from django.urls import path, include
from users.admin_area import urls as admin_area_urls

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/users/', include('users.urls')),
    path('api/admin/', include(admin_area_urls)),
]
