import logging

from celery.signals import worker_ready

logger = logging.getLogger(__name__)


@worker_ready.connect(dispatch_uid="threadline.startup_recovery")
def recover_processing_emails_on_worker_ready(sender=None, **kwargs):
    """
    Requeue stale processing emails when a Celery worker becomes ready.

    This module is intentionally named as a Celery bootstrap hook so other
    apps can follow the same pattern for their own worker startup logic.
    """
    try:
        logger.info("Threadline worker_ready signal received")
        from threadline.services.startup_recovery import (
            recover_stuck_processing_emails,
        )

        result = recover_stuck_processing_emails()
        logger.info(
            "Threadline startup recovery completed: %s",
            result,
        )
    except Exception as exc:
        logger.exception(
            "Threadline startup recovery failed on worker ready: %s", exc
        )
