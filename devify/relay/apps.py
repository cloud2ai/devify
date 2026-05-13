"""Django app config for Relay."""

from django.apps import AppConfig


class RelayConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "relay"
    verbose_name = "Relay"

    def ready(self):
        import relay.tasks  # noqa: F401
        import relay.celery_bootstrap  # noqa: F401
