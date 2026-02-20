from pathlib import Path
# 👆this will convert string path from __file__ into a pth object

import os
# 👆 provides access to environment variables and OS-level operations like os.getenv().

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

raw_hosts = os.getenv("DJANGO_ALLOWED_HOSTS", "")
ALLOWED_HOSTS = raw_hosts.split(",") if raw_hosts else []
# 👆 List of domains allowed to serve this app when DEBUG is False. Required for production security.

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

STATIC_URL = 'static/' # 👉 url prefix for serving static files like css, js, and images

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
# 👆 sets the default primary key type for new models to bigautofield (large auto-incrementing integer)

AUTH_USER_MODEL = 'core.CustomUser'
# 👆 tells django to use a custom user model defined in core/models.py instead of the default one

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
# 👆 allows frontend origins to send csrf-protected requests (needed when using react in development)

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
# 👆 allows the frontend to make cross-origin api calls to the backend (used by axios or fetch)

CORS_ALLOW_CREDENTIALS = True


# 👉 summary:
# this settings file defines the core configuration for the django backend.
# it handles environment variables, installed apps, middleware, database setup,
# custom user model, authentication (jwt), cors and csrf policies, and other
# project-wide defaults required for development and production readiness.
