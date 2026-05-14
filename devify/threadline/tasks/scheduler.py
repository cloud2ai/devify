import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from agentcore_task.adapters.django import prevent_duplicate_task
from threadline.models import EmailMessage, EmailTask
from threadline.tasks.cleanup import (
    EmailCleanupManager,
    EmailTaskCleanupManager,
    ShareLinkCleanupManager,
)
from threadline.tasks.email_fetch import imap_email_fetch, haraka_email_fetch
from threadline.tasks.email_workflow import process_email_workflow
from threadline.state_machine import EmailStatus
from threadline.utils.task_cleanup import cleanup_stale_tasks
from threadline.utils.task_tracer import TaskTracer, use_task_tracer

logger = logging.getLogger(__name__)


@shared_task
@prevent_duplicate_task(
    "email_fetch", timeout=settings.TASK_TIMEOUT_MINUTES * 60
)
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
    3. Task lock mechanism (TASK_TIMEOUT_MINUTES converted to seconds)
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
            f"{tracer.context_summary()} "
            "Starting unified email fetch scheduling"
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

        imap_context = tracer.context_summary({"task_id": imap_result.id})
        haraka_context = tracer.context_summary({"task_id": haraka_result.id})
        logger.info(
            f"{imap_context} IMAP email fetch task started: "
            f"{imap_result.id}"
        )
        logger.info(
            f"{haraka_context} Haraka email fetch task started: "
            f"{haraka_result.id}"
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
@prevent_duplicate_task("haraka_cleanup", timeout=30 * 60)
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
                f"{tracer.context_summary()} "
                "Starting Haraka email files cleanup scheduler"
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
            f"{tracer.context_summary()} "
            f"Haraka cleanup scheduling failed: {exc}"
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
                f"{tracer.context_summary()} "
                "Starting share link cleanup scheduler"
            )
            cleanup_manager = ShareLinkCleanupManager()
            result = cleanup_manager.cleanup_expired_share_links()

        logger.info(
            f"{tracer.context_summary()} "
            f"Share link cleanup completed: {result}"
        )
        return result

    except Exception as exc:
        tracer.fail_task({"error": str(exc)}, str(exc))
        logger.error(
            f"{tracer.context_summary()} "
            f"Share link cleanup scheduling failed: {exc}"
        )
        raise


@shared_task
@prevent_duplicate_task(
    "stuck_email_reset", timeout=settings.TASK_TIMEOUT_MINUTES * 60
)
def schedule_reset_stuck_processing_emails(timeout_minutes=30):
    """
    Reset emails stuck in FETCHED or PROCESSING state.
    """
    tracer = TaskTracer(
        "STUCK_EMAIL_RESET",
        module="threadline",
    )
    try:
        cleanup_stale_tasks(
            timeout_minutes=settings.TASK_TIMEOUT_MINUTES,
            task_types=EmailTask.TaskType.STUCK_EMAIL_RESET,
        )
        tracer.create_task(
            {
                "timeout_minutes": timeout_minutes,
                "started": timezone.now().isoformat(),
            }
        )
        now = timezone.now()
        stuck_emails = EmailMessage.objects.filter(
            status__in=(
                EmailStatus.FETCHED.value,
                EmailStatus.PROCESSING.value,
            ),
            updated_at__lt=now - timedelta(minutes=timeout_minutes),
        )

        fetched_retry_count = 0
        fetched_failed_count = 0
        processing_failed_count = 0

        for email in stuck_emails:
            if email.status == EmailStatus.FETCHED.value:
                if email.fetch_retry_count == 0:
                    email.fetch_retry_count = 1
                    email.error_message = (
                        "Email stuck in FETCHED status, retrying "
                        "workflow trigger"
                    )
                    email.save(
                        update_fields=["fetch_retry_count", "error_message"]
                    )
                    process_email_workflow.delay(str(email.id))
                    fetched_retry_count += 1
                else:
                    email.status = EmailStatus.FAILED.value
                    email.error_message = (
                        "Email stuck in FETCHED status after retry. "
                        "Possible Celery worker issue - check worker logs"
                    )
                    email.save(update_fields=["status", "error_message"])
                    fetched_failed_count += 1
            elif email.status == EmailStatus.PROCESSING.value:
                email.status = EmailStatus.FAILED.value
                email.error_message = (
                    f"Processing stuck for over {timeout_minutes} minutes. "
                    "Requires manual intervention."
                )
                email.save(update_fields=["status", "error_message"])
                processing_failed_count += 1

        total_handled = (
            fetched_retry_count
            + fetched_failed_count
            + processing_failed_count
        )
        tracer.complete_task(
            {
                "fetched_retry_count": fetched_retry_count,
                "fetched_failed_count": fetched_failed_count,
                "processing_failed_count": processing_failed_count,
                "total_handled": total_handled,
                "completed_at": timezone.now().isoformat(),
            }
        )
        return {
            "fetched_retry_count": fetched_retry_count,
            "fetched_failed_count": fetched_failed_count,
            "processing_failed_count": processing_failed_count,
            "total_handled": total_handled,
            "status": "completed",
        }
    except Exception as exc:
        tracer.fail_task({"error": str(exc)}, str(exc))
        logger.error(f"Stuck email reset failed: {exc}")
        raise


@shared_task
@prevent_duplicate_task(
    "stuck_email_reset", timeout=settings.TASK_TIMEOUT_MINUTES * 60
)
def schedule_reset_stuck_emails(timeout_minutes=30):
    """
    Backward-compatible alias for schedule_reset_stuck_processing_emails.
    """
    return schedule_reset_stuck_processing_emails(timeout_minutes=timeout_minutes)


@shared_task
@prevent_duplicate_task(
    "email_task_cleanup", timeout=settings.TASK_TIMEOUT_MINUTES * 60
)
def schedule_email_task_cleanup():
    """
    Clean up old EmailTask records.
    """
    tracer = TaskTracer(
        "TASK_CLEANUP",
        module="threadline",
    )
    try:
        with use_task_tracer(tracer):
            logger.info(
                f"{tracer.context_summary()} "
                "Starting EmailTask cleanup scheduler"
            )
            cleanup_manager = EmailTaskCleanupManager()
            result = cleanup_manager.cleanup_email_tasks()
        logger.info(
            f"{tracer.context_summary()} "
            f"EmailTask cleanup completed: {result}"
        )
        return result
    except Exception as exc:
        logger.error(
            f"{tracer.context_summary()} "
            f"EmailTask cleanup failed: {exc}"
        )
        raise
