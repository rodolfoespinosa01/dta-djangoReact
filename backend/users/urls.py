from django.urls import path, include

urlpatterns = [
    path('admin/', include('users.admin_area.urls')),
    path('superadmin/', include('users.superadmin_area.urls')),
    path('client/', include('users.client_area.urls')),
]
