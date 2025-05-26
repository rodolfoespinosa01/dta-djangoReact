from django.apps import AppConfig  # 👉 base class for configuring a Django app

class AreaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'  # 👉 sets default ID field type for models
    name = 'users.admin_area'  # 👉 path to this app's module (used for namespacing and imports)

    def ready(self):
        # 🔔 import signals when the app is ready
        # ensures signal handlers (like post_migrate) are registered at startup
        import users.admin_area.signals


# 👉 summary:
# configures the admin_area Django app.
# imports signal listeners when the app starts to support automatic logic like plan creation.
# typically used for initializing app-specific behavior at runtime.