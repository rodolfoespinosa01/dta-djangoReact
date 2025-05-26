import os  # 👉 used to set environment variables for django's configuration

from django.core.wsgi import get_wsgi_application  # 👉 gets the wsgi-compatible django application


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
# 👆 sets the default settings module for the wsgi app to use (should match your project structure)


application = get_wsgi_application()
# 👆 creates the wsgi application instance for serving http requests (used by servers like gunicorn or mod_wsgi)


# 👉 summary:
# sets up the wsgi entry point for the django project.
# required when deploying with wsgi-compatible servers in production (e.g. gunicorn, apache).
# this is the standard entry point for traditional synchronous django apps.
