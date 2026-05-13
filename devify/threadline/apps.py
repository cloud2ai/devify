import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class ThreadlineConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "threadline"
    app_label = "threadline"

    def ready(self):
        """Register signal handlers when the app is ready."""
        logger.info("ThreadlineConfig.ready() called")
        # Celery autodiscovery only imports the package entrypoint.
        # Import the concrete task modules explicitly so shared_task
        # decorators register every Threadline task in the worker registry.
        import threadline.tasks.email_merge  # noqa: F401
        import threadline.tasks.email_fetch  # noqa: F401
        import threadline.tasks.email_workflow  # noqa: F401
        import threadline.tasks.scheduler  # noqa: F401
