import logging
from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from threadline.models import EmailMessage, EmailTask
from threadline.state_machine import EmailStatus
from threadline.tasks.email_fetch import imap_email_fetch, haraka_email_fetch
from threadline.tasks.cleanup import (EmailCleanupManager,
                                      EmailTaskCleanupManager)
from threadline.utils.task_cleanup import cleanup_stale_tasks
from threadline.utils.task_lock import prevent_duplicate_task
from threadline.utils.task_tracer import TaskTracer
from django.conf import settings

logger = logging.getLogger(__name__)

# Configuration for stuck email handling
# Only PROCESSING state can get stuck, but using list for future extensibility
STUCK_EMAIL_STATUSES = [EmailStatus.PROCESSING.value]

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
    2. Clean up stale tasks
    3. Schedule both IMAP and Haraka email fetch tasks
    4. Task lock mechanism (TASK_TIMEOUT_MINUTES timeout)
    5. Error handling and monitoring
    """
    try:
        logger.info("Starting unified email fetch scheduling")

        # Clean up stale tasks for IMAP and Haraka fetch
        cleanup_stale_tasks(
            task_types=[
                EmailTask.TaskType.IMAP_FETCH,
                EmailTask.TaskType.HARAKA_FETCH
            ]
        )

        # Schedule both email fetch tasks
        # Processing will be triggered automatically when each completes
        imap_result = imap_email_fetch.delay()
        haraka_result = haraka_email_fetch.delay()

        logger.info(f"IMAP email fetch task started: {imap_result.id}")
        logger.info(f"Haraka email fetch task started: {haraka_result.id}")

        return {
            "imap_task_id": imap_result.id,
            "haraka_task_id": haraka_result.id,
            "status": "scheduled"
        }

    except Exception as exc:
        logger.error(f"Email fetch scheduling failed: {exc}")
        raise


@shared_task
@prevent_duplicate_task(
    "stuck_email_reset", timeout=settings.TASK_TIMEOUT_MINUTES)
def schedule_reset_stuck_processing_emails(timeout_minutes=30):
    """
    Scan and mark emails stuck in PROCESSING state as FAILED.

    Only emails in PROCESSING state can get stuck. To avoid infinite retry
    loops, stuck emails are marked as FAILED and require manual intervention.

    Uses lock mechanism to prevent duplicate execution.

    Args:
        timeout_minutes (int): Minutes after which emails are considered stuck
    """
    cleanup_stale_tasks(
        timeout_minutes=settings.TASK_TIMEOUT_MINUTES,
        task_types=EmailTask.TaskType.STUCK_EMAIL_RESET
    )

    tracer = TaskTracer(EmailTask.TaskType.STUCK_EMAIL_RESET)
    tracer.create_task({
        'timeout_minutes': timeout_minutes,
        'started': timezone.now().isoformat()
    })

    try:
        now = timezone.now()

        stuck_emails = EmailMessage.objects.filter(
            status__in=STUCK_EMAIL_STATUSES,
            updated_at__lt=now - timedelta(minutes=timeout_minutes)
        )

        failed_count = 0
        for email in stuck_emails:
            logger.warning(
                f"Email {email.id} stuck in {EmailStatus.PROCESSING.name} "
                f"for {timeout_minutes}+ minutes, marking as "
                f"{EmailStatus.FAILED.name}"
            )

            email.status = EmailStatus.FAILED.value
            email.error_message = (
                f"Processing stuck for over {timeout_minutes} minutes. "
                f"Requires manual intervention."
            )
            email.save(update_fields=['status', 'error_message'])

            failed_count += 1

        if failed_count > 0:
            logger.info(
                f"Marked {failed_count} stuck emails as "
                f"{EmailStatus.FAILED.name}"
            )

        tracer.complete_task({
            'failed_count': failed_count,
            'completed_at': timezone.now().isoformat()
        })

        return {
            'failed_count': failed_count,
            'status': 'completed'
        }

    except Exception as exc:
        tracer.fail_task({'error': str(exc)}, str(exc))
        logger.error(f"Stuck email reset failed: {exc}")
        raise


@shared_task
@prevent_duplicate_task("haraka_cleanup", timeout=30)
def schedule_haraka_cleanup():
    """
    Haraka email files cleanup scheduler

    This task schedules the cleanup of Haraka email files from all directories.
    It runs independently of the main email processing workflow.
    """
    try:
        logger.info("Starting Haraka email files cleanup scheduler")

        cleanup_manager = EmailCleanupManager()
        result = cleanup_manager.cleanup_haraka_files()

        logger.info(f"Haraka cleanup completed: {result}")
        return result

    except Exception as exc:
        logger.error(f"Haraka cleanup scheduling failed: {exc}")
        raise


@shared_task
@prevent_duplicate_task("email_task_cleanup", timeout=30)
def schedule_email_task_cleanup():
    """
    EmailTask records cleanup scheduler

    This task schedules the cleanup of old EmailTask records.
    It runs independently of the main email processing workflow.
    """
    try:
        logger.info("Starting EmailTask cleanup scheduler")

        task_cleanup_manager = EmailTaskCleanupManager()
        result = task_cleanup_manager.cleanup_email_tasks()

        logger.info(f"EmailTask cleanup completed: {result}")
        return result

    except Exception as exc:
        logger.error(f"EmailTask cleanup scheduling failed: {exc}")
        raise
