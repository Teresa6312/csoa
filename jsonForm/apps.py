from django.apps import AppConfig


class JsonformConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'jsonForm'

    def ready(self):
        import jsonForm.signals