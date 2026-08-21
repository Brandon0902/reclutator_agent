from django.apps import AppConfig


class PostulacionesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "postulaciones"

    def ready(self):
        from . import checks  # noqa: F401
