from django.apps import AppConfig
from django.db.models.signals import post_migrate


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Site configuration"

    def ready(self):
        from .seed import seed_reference_data

        post_migrate.connect(seed_reference_data, sender=self, dispatch_uid="core_seed_reference_data")
