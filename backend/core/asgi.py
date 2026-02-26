import os  # 👉 used to set environment variables for the app

from django.core.asgi import get_asgi_application  # 👉 gets the asgi-compatible django application
from django.conf import settings
from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
# 👉 sets the default settings module for the asgi app to use

application = get_asgi_application()
# 👉 creates the asgi application instance for handling async requests (e.g. websockets, long-polling)

if settings.DEBUG:
    # Serve Django/admin static assets in local dev when running via uvicorn.
    application = ASGIStaticFilesHandler(application)

# 👉 summary:
# initializes the asgi entry point for the django project.
# used when deploying with asgi servers (like daphne or uvicorn) to support async features and real-time communication.
