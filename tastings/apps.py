from django.apps import AppConfig


class TastingsConfig(AppConfig):
    default_auto_field = "django_mongodb_backend.fields.ObjectIdAutoField"
    name = "tastings"
