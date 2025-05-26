import os  # 👉 used to set environment variables for the app

from django.core.asgi import get_asgi_application  # 👉 gets the asgi-compatible django application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
# 👉 sets the default settings module for the asgi app to use

application = get_asgi_application()
# 👉 creates the asgi application instance for handling async requests (e.g. websockets, long-polling)

# 👉 summary:
# initializes the asgi entry point for the django project.
# used when deploying with asgi servers (like daphne or uvicorn) to support async features and real-time communication.
