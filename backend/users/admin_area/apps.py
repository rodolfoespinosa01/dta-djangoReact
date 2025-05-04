from django.apps import AppConfig

class AdminplansConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'adminplans'

    def ready(self):
        import adminplans.signals
