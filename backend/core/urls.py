from django.contrib import admin  # 👉 imports the built-in django admin interface
from django.urls import path, include  # 👉 used to define url routes and include other app-specific urls


urlpatterns = [
    path('admin/', admin.site.urls),  # 👉 routes /admin/ to the django admin dashboard
    path('api/users/', include('users.urls')),  # 👉 includes all user-related api routes under /api/users/
]


# 👉 summary:
# defines the main url routing configuration for the project.
# connects the admin interface and delegates user-related routes to the users app.
# all urls registered in users/urls.py will be prefixed with /api/users/