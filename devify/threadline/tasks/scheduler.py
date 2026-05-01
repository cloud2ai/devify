import logging
from celery import shared_task
from django.utils import timezone

from threadline.tasks.email_fetch import imap_email_fetch, haraka_email_fetch
from threadline.tasks.cleanup import (
    EmailCleanupManager,
    ShareLinkCleanupManager,
)
from threadline.utils.task_lock import prevent_duplicate_task
from threadline.utils.task_tracer import TaskTracer, use_task_tracer
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task
@prevent_duplicate_task("email_fetch", timeout=settings.TASK_TIMEOUT_MINUTES)
def schedule_email_fetch():
    """
    Unified email fetch scheduler

    This is the main entry point for all email fetching operations.
    Schedules both IMAP and Haraka email fetch tasks.

    Note: Email processing will be triggered automatically when each
    fetch task completes, ensuring timely processing.

    Responsibilities:
    1. Check task locks (handled by decorator)
    2. Schedule both IMAP and Haraka email fetch tasks
    3. Task lock mechanism (TASK_TIMEOUT_MINUTES timeout)
    4. Error handling and monitoring
    """
    tracer = TaskTracer(
        "EMAIL_FETCH_SCHEDULER",
        module="threadline",
    )
    try:
        tracer.create_task(
            {
                "started_at": timezone.now().isoformat(),
                "status": "starting",
            }
        )
        tracer.append_task(
            "SCHEDULE_START",
            "Email fetch scheduler started",
            {"started_at": timezone.now().isoformat()},
        )
        logger.info(
            f"{tracer.context_summary()} Starting unified email fetch scheduling"
        )

        # Schedule both email fetch tasks
        # Processing will be triggered automatically when each completes
        imap_result = imap_email_fetch.delay()
        haraka_result = haraka_email_fetch.delay()
        tracer.append_task(
            "SCHEDULE_DISPATCH",
            "Email fetch jobs dispatched",
            {
                "imap_task_id": imap_result.id,
                "haraka_task_id": haraka_result.id,
            },
        )

        logger.info(
            f"{tracer.context_summary({'task_id': imap_result.id})} IMAP email fetch task started: {imap_result.id}"
        )
        logger.info(
            f"{tracer.context_summary({'task_id': haraka_result.id})} Haraka email fetch task started: {haraka_result.id}"
        )
        tracer.complete_task(
            {
                "imap_task_id": imap_result.id,
                "haraka_task_id": haraka_result.id,
                "status": "scheduled",
                "completed_at": timezone.now().isoformat(),
            }
        )

        return {
            "imap_task_id": imap_result.id,
            "haraka_task_id": haraka_result.id,
            "status": "scheduled",
        }

    except Exception as exc:
        tracer.append_task(
            "SCHEDULE_ERROR",
            f"Email fetch scheduling failed: {exc}",
            {"error": str(exc)},
        )
        tracer.fail_task({"error": str(exc)}, str(exc))
        logger.error(
            f"{tracer.context_summary()} Email fetch scheduling failed: {exc}"
        )
        raise


@shared_task
@prevent_duplicate_task("haraka_cleanup", timeout=30)
def schedule_haraka_cleanup():
    """
    Haraka email files cleanup scheduler

    This task schedules the cleanup of Haraka email files from all directories.
    It runs independently of the main email processing workflow.
    """
    tracer = TaskTracer(
        "HARAKA_CLEANUP",
        module="threadline",
    )
    try:
        with use_task_tracer(tracer):
            logger.info(
                f"{tracer.context_summary()} Starting Haraka email files cleanup scheduler"
            )
            cleanup_manager = EmailCleanupManager()
            result = cleanup_manager.cleanup_haraka_files()

        logger.info(
            f"{tracer.context_summary()} Haraka cleanup completed: {result}"
        )
        return result

    except Exception as exc:
        tracer.fail_task({"error": str(exc)}, str(exc))
        logger.error(
            f"{tracer.context_summary()} Haraka cleanup scheduling failed: {exc}"
        )
        raise


@shared_task
@prevent_duplicate_task("share_link_cleanup", timeout=30)
def schedule_share_link_cleanup():
    """
    Share link cleanup scheduler.

    Deactivates expired share links to ensure stale URLs are not accessible.
    """
    tracer = TaskTracer(
        "SHARE_LINK_CLEANUP",
        module="threadline",
    )
    try:
        with use_task_tracer(tracer):
            logger.info(
                f"{tracer.context_summary()} Starting share link cleanup scheduler"
            )
            cleanup_manager = ShareLinkCleanupManager()
            result = cleanup_manager.cleanup_expired_share_links()

        logger.info(
            f"{tracer.context_summary()} Share link cleanup completed: {result}"
        )
        return result

    except Exception as exc:
        tracer.fail_task({"error": str(exc)}, str(exc))
        logger.error(
            f"{tracer.context_summary()} Share link cleanup scheduling failed: {exc}"
        )
        raise
