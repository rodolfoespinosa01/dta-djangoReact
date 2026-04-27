from pathlib import Path
# 👆this will convert string path from __file__ into a pth object

import os
# 👆 provides access to environment variables and OS-level operations like os.getenv().
import socket

from dotenv import load_dotenv
# 👆 Loads environment variables from the .env file into the app’s environment.
# This is required to make os.getenv("KEY") work with values defined in .env.

from datetime import timedelta


BASE_DIR = Path(__file__).resolve().parent.parent
# 👆 BASE_DIR ends up being /Desktop/dta-djangoreact/backend
# __file__ = /backend/core/settings.py
# .resolve() turns it into an absolute path 👉 /Users/yourname/Desktop/dta-djangoreact/backend/core/settings.py
# .parent goes up one level 👉 /Users/yourname/Desktop/dta-djangoreact/backend/core
# .parent goes up another level 👉 /Users/yourname/Desktop/dta-djangoreact/backend

load_dotenv(BASE_DIR / '.env')
# 👆load environment variables from the .env file located at the project base directory
# this allows sensitive settings (like secret keys and database URLs) to be managed securely
# outside of the source code, and accessed via os.getenv().


STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
# 👆 Pulls your Stripe secret key from the .env file

STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
# 👆 Gets your Stripe webhook secret (used to verify incoming events)

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
# 👆 Loads Django's secret key securely from the .env file

DEBUG = os.getenv("DJANGO_DEBUG") == "true"
# 👆 Enables debug mode (shows detailed error pages). WARNING: Never use this in production!


def _detect_local_ipv4():
    """
    Best-effort local LAN IP detection for phone/tablet testing in DEBUG.
    """
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # No packet is sent; this resolves the outbound local interface.
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        return ip if ip and ip != "127.0.0.1" else None
    except Exception:
        return None
    finally:
        if sock is not None:
            try:
                sock.close()
            except Exception:
                pass

raw_hosts = os.getenv("DJANGO_ALLOWED_HOSTS", "")
ALLOWED_HOSTS = raw_hosts.split(",") if raw_hosts else []
# 👆 List of domains allowed to serve this app when DEBUG is False. Required for production security.
if DEBUG and not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]", ".lvh.me"]
    # 👆 dev-friendly default so local subdomain previews like coach.lvh.me work without DisallowedHost.
if DEBUG:
    _local_ipv4 = _detect_local_ipv4()
    if _local_ipv4 and _local_ipv4 not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_local_ipv4)

INSTALLED_APPS = [
    'django.contrib.admin', # 👉 built-in Django admin interface
    'django.contrib.auth', # 👉 handles user authentication (login, password, permissions)
    'django.contrib.contenttypes', # 👉 tracks model types for permissions and generic relations
    'django.contrib.sessions', # 👉 enables session storage (cookies and server-side sessions)
    'django.contrib.messages', # 👉 built-in messaging framework (used for alerts/notifications)
    'django.contrib.staticfiles', # 👉 manages serving static files (CSS, JS, images)

    'corsheaders', # 👉 handles Cross-Origin Resource Sharing (CORS) for API access
    'rest_framework', # 👉 django REST Framework (DRF) for building APIs

    'core', # 👉 core app (settings, shared utils, base config)
    'users', # 👉 custom app for user-related logic (models, views, auth)
    'users.admin_area', # 👉 submodule for admin-specific views and logic
    'users.client_area', # 👉 client/end-user onboarding + dashboard logic
    'utility', # 👉 general utility functions/helpers used across the project
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware', # 👉 handles cors headers for cross-origin api requests

    'django.middleware.security.SecurityMiddleware', # 👉 adds security headers (ssl redirect, hsts, etc.)
    'django.contrib.sessions.middleware.SessionMiddleware', # 👉 manages sessions across requests using cookies
    'django.middleware.locale.LocaleMiddleware', # 👉 activates language selection per request (accept-language/cookies/etc.)
    'django.middleware.common.CommonMiddleware', # 👉 performs basic request/response operations (e.g. url normalization)
    'django.middleware.csrf.CsrfViewMiddleware', # 👉 protects against cross-site request forgery attacks
    'django.contrib.auth.middleware.AuthenticationMiddleware', # 👉 associates users with requests using sessions
    'django.contrib.messages.middleware.MessageMiddleware', # 👉 enables temporary messages via the messages framework
    'django.middleware.clickjacking.XFrameOptionsMiddleware', # 👉 prevents clickjacking by setting x-frame-options header
]

ROOT_URLCONF = 'core.urls'
# 👆 tells django to look in core/urls.py for the main url routing config

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'
# 👆 tells django where to find the wsgi entry point for deploying with wsgi servers (like gunicorn or mod_wsgi)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT'),
    }
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',  # 👉 uses jwt tokens for authenticating api requests
    ),
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30), # 👉 access tokens expire 30 minutes after login (user must refresh)
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1), # 👉 refresh tokens expire after 1 day (user must log in again after that)
    'AUTH_HEADER_TYPES': ('Bearer',), # 👉 expects "authorization: bearer <token>" in request headers
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',), # 👉 uses standard jwt access tokens
    'TOKEN_OBTAIN_SERIALIZER': 'core.serializers.token_serializer.CustomTokenObtainPairSerializer', # 👉 custom login serializer (e.g. adds email or roles to token)
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        # 👆 prevents using passwords that are too similar to user info (like username or email)
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        # 👆 enforces a minimum password length (default is 8 characters)
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
        # 👆 blocks overly common passwords like "password123" or "admin"
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
        # 👆 prevents passwords that are fully numeric (e.g. "12345678")
    },
]

AUTHENTICATION_BACKENDS = [
    'users.backends.EmailBackend', # 👉 custom backend that allows login using email instead of username
    'django.contrib.auth.backends.ModelBackend', # 👉 default django backend (username + password)
]

LANGUAGE_CODE = 'en' # 👉 sets english as the default language for the project

LANGUAGES = [
    ('en', 'English'),
    ('es', 'Spanish'),
]

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

TIME_ZONE = 'America/New_York' # 👉 sets the server timezone (currently set to utc)

USE_I18N = True  # 👉 enables django's internationalization system (for translations)

USE_TZ = True  # 👉 stores all datetime objects in utc and converts to local time on display

STATIC_URL = '/static/' # 👉 url prefix for serving static files like css, js, and images
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
# 👆 sets the default primary key type for new models to bigautofield (large auto-incrementing integer)

AUTH_USER_MODEL = 'core.CustomUser'
# 👆 tells django to use a custom user model defined in core/models.py instead of the default one

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://localhost:3000",
    "https://127.0.0.1:3000",
    "http://*.lvh.me:3000",
    "https://*.lvh.me:3000",
]
# 👆 allows frontend origins to send csrf-protected requests (needed when using react in development)

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://localhost:3000",
    "https://127.0.0.1:3000",
]
# 👆 allows the frontend to make cross-origin api calls to the backend (used by axios or fetch)
if DEBUG:
    _local_ipv4 = _detect_local_ipv4()
    if _local_ipv4:
        CORS_ALLOWED_ORIGINS.extend(
            [
                f"http://{_local_ipv4}:3000",
                f"https://{_local_ipv4}:3000",
            ]
        )

CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https?://([a-z0-9-]+\.)?lvh\.me:3000$",
]

CORS_ALLOW_CREDENTIALS = True
if DEBUG:
    _local_ipv4 = _detect_local_ipv4()
    if _local_ipv4:
        CSRF_TRUSTED_ORIGINS.extend(
            [
                f"http://{_local_ipv4}:3000",
                f"https://{_local_ipv4}:3000",
            ]
        )

FRONTEND_URL = os.getenv("FRONTEND_URL") or "http://localhost:3000"
GOOGLE_OAUTH_CLOCK_SKEW_SECONDS = int(os.getenv("GOOGLE_OAUTH_CLOCK_SKEW_SECONDS") or "10")

USDA_FDC_API_KEY = os.getenv("USDA_FDC_API_KEY") or os.getenv("USDA_FOODDATA_API_KEY") or ""
USDA_FOODDATA_API_KEY = USDA_FDC_API_KEY
USDA_FOODDATA_BASE_URL = os.getenv("USDA_FOODDATA_BASE_URL") or "https://api.nal.usda.gov/fdc/v1"
USDA_FOODDATA_TIMEOUT_SECONDS = int(os.getenv("USDA_FOODDATA_TIMEOUT_SECONDS") or "8")
OPEN_FOOD_FACTS_BASE_URL = os.getenv("OPEN_FOOD_FACTS_BASE_URL") or "https://world.openfoodfacts.org"
OPEN_FOOD_FACTS_USER_AGENT = os.getenv("OPEN_FOOD_FACTS_USER_AGENT") or "DTA-Diet-Generator/1.0 (support@dtameals.com)"
OPEN_FOOD_FACTS_TIMEOUT_SECONDS = int(os.getenv("OPEN_FOOD_FACTS_TIMEOUT_SECONDS") or "8")


CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL") or os.getenv("REDIS_URL") or "redis://127.0.0.1:6379/0"
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND") or CELERY_BROKER_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE


# 👉 summary:
# this settings file defines the core configuration for the django backend.
# it handles environment variables, installed apps, middleware, database setup,
# custom user model, authentication (jwt), cors and csrf policies, and other
# project-wide defaults required for development and production readiness.
