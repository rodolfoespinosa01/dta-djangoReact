from django.apps import AppConfig

class AreaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users.admin_area'

    def ready(self):
        import users.admin_area.signals
