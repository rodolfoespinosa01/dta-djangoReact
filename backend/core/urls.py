from django.contrib import admin  # 👉 imports the built-in django admin interface
from django.urls import path, include  # 👉 used to define url routes and include other app-specific urls
from django.http import HttpResponse
from rest_framework.permissions import AllowAny
from rest_framework.schemas import get_schema_view
from core.api_meta import error_codes

schema_view = get_schema_view(
    title="DTA API",
    description="Versioned API schema for web and mobile clients.",
    version="1.0.0",
    permission_classes=[AllowAny],
)


def api_docs_view(_request):
    return HttpResponse(
        '<html><body style="font-family:Arial,sans-serif;padding:16px;">'
        '<h1>DTA API Docs</h1>'
        '<p>OpenAPI schema: <a href="/api/v1/schema/">/api/v1/schema/</a></p>'
        '<p>Error codes: <a href="/api/v1/meta/error-codes/">/api/v1/meta/error-codes/</a></p>'
        '</body></html>'
    )

urlpatterns = [
    path('admin/', admin.site.urls),  # 👉 routes /admin/ to the django admin dashboard
    path('api/users/', include('users.urls')),  # 👉 includes all user-related api routes under /api/users/
    path('api/v1/users/', include('users.urls')),  # 👉 versioned alias for mobile/web clients
    path('api/v1/schema/', schema_view, name='api_schema'),
    path('api/v1/docs/', api_docs_view, name='api_docs'),
    path('api/v1/meta/error-codes/', error_codes, name='api_error_codes'),
]


# 👉 summary:
# defines the main url routing configuration for the project.
# connects the admin interface and delegates user-related routes to the users app.
# all urls registered in users/urls.py will be prefixed with /api/users/
