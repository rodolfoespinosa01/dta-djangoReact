from django.apps import AppConfig  # 👉 base class for configuring django apps

class CoreConfig(AppConfig):  # 👉 defines configuration for the core app
    default_auto_field = "django.db.models.BigAutoField"  # 👉 sets default primary key type for models in this app
    name = "core"  # 👉 sets the app label used by django for referencing this app internally


# 👉 summary:
# configures the core app within the django project.
# sets the default auto field and internal app name used by django for model and app registration.
