import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class ThreadlineConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'threadline'
    app_label = 'threadline'

    def ready(self):
        """Register signal handlers when the app is ready."""
        import threadline.signals
        self._setup_worker_cleanup()

    def _setup_worker_cleanup(self):
        """
        Setup worker startup cleanup.

        Registers cleanup to run synchronously when Celery worker starts,
        ensuring clean state before processing tasks.
        """
        try:
            from celery.signals import worker_ready
            from threadline.utils.task_cleanup import startup_cleanup

            @worker_ready.connect
            def cleanup_on_worker_start(sender, **kwargs):
                logger.info("Worker started, running cleanup...")
                result = startup_cleanup()
                logger.info(f"Cleanup completed: {result}")

        except ImportError:
            pass
