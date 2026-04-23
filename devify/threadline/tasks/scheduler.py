import logging
from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from threadline.models import EmailMessage, EmailTask
from threadline.state_machine import EmailStatus
from threadline.tasks.email_fetch import imap_email_fetch, haraka_email_fetch
from threadline.tasks.email_workflow import process_email_workflow
from threadline.tasks.cleanup import (
    EmailCleanupManager,
    EmailTaskCleanupManager,
    ShareLinkCleanupManager,
)
from threadline.utils.task_cleanup import cleanup_stale_tasks
from threadline.utils.task_lock import prevent_duplicate_task
from threadline.utils.task_tracer import TaskTracer, use_task_tracer
from django.conf import settings

logger = logging.getLogger(__name__)

# Configuration for stuck email handling
# Both FETCHED and PROCESSING states can get stuck
STUCK_EMAIL_STATUSES = [
    EmailStatus.FETCHED.value,
    EmailStatus.PROCESSING.value,
]


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
    tracer = TaskTracer(
        "EMAIL_FETCH_SCHEDULER",
        module="threadline",
        track_legacy=False,
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

        # Clean up stale tasks for IMAP and Haraka fetch
        cleanup_stale_tasks(
            task_types=[
                EmailTask.TaskType.IMAP_FETCH,
                EmailTask.TaskType.HARAKA_FETCH,
            ]
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
@prevent_duplicate_task(
    "stuck_email_reset", timeout=settings.TASK_TIMEOUT_MINUTES
)
def schedule_reset_stuck_emails(timeout_minutes=30):
    """
    Scan and handle emails stuck in FETCHED or PROCESSING state.

    This task handles two types of stuck emails:
    1. FETCHED: Emails that were fetched but workflow was never triggered
       - First timeout: Retry workflow trigger once
       - Second timeout: Mark as FAILED (possible worker issue)
    2. PROCESSING: Emails stuck during workflow execution
       - Mark as FAILED and require manual intervention

    Uses lock mechanism to prevent duplicate execution.

    Args:
        timeout_minutes (int): Minutes after which emails are considered stuck
    """
    cleanup_stale_tasks(
        timeout_minutes=settings.TASK_TIMEOUT_MINUTES,
        task_types=EmailTask.TaskType.STUCK_EMAIL_RESET,
    )

    tracer = TaskTracer(EmailTask.TaskType.STUCK_EMAIL_RESET)
    tracer.create_task(
        {
            "timeout_minutes": timeout_minutes,
            "started": timezone.now().isoformat(),
        }
    )
    tracer.append_task(
        "CLEANUP_START",
        "Stuck email reset started",
        {
            "timeout_minutes": timeout_minutes,
            "started": timezone.now().isoformat(),
        },
    )

    try:
        now = timezone.now()

        stuck_emails = EmailMessage.objects.filter(
            status__in=STUCK_EMAIL_STATUSES,
            updated_at__lt=now - timedelta(minutes=timeout_minutes),
        )
        tracer.append_task(
            "CLEANUP_SCAN",
            "Loaded stuck emails for evaluation",
            {
                "stuck_count": stuck_emails.count(),
                "timeout_minutes": timeout_minutes,
            },
        )

        fetched_retry_count = 0
        fetched_failed_count = 0
        processing_failed_count = 0

        for email in stuck_emails:
            if email.status == EmailStatus.FETCHED.value:
                if email.fetch_retry_count == 0:
                    logger.warning(
                        f"Email {email.id} stuck in FETCHED status "
                        f"for {timeout_minutes}+ minutes, retrying "
                        f"workflow trigger (attempt 1)"
                    )

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

                    logger.info(f"Re-triggered workflow for email {email.id}")

                else:
                    logger.error(
                        f"Email {email.id} stuck in FETCHED status after "
                        f"retry, marking as FAILED (possible Celery "
                        f"worker issue)"
                    )

                    # State transition from FETCHED to FAILED is now valid
                    # in state machine
                    email.status = EmailStatus.FAILED.value
                    email.error_message = (
                        f"Email stuck in FETCHED status after retry. "
                        f"Possible Celery worker issue - check worker logs"
                    )
                    email.save(update_fields=["status", "error_message"])

                    fetched_failed_count += 1

            elif email.status == EmailStatus.PROCESSING.value:
                logger.warning(
                    f"Email {email.id} stuck in PROCESSING status "
                    f"for {timeout_minutes}+ minutes, marking as FAILED"
                )

                # Preserve original error message and add timeout info
                original_error = email.error_message or ""
                timeout_info = (
                    f"[TIMEOUT] Processing stuck for over "
                    f"{timeout_minutes} minutes. "
                )
                if original_error:
                    combined_error = (
                        f"{timeout_info}Original error: {original_error}"
                    )
                else:
                    combined_error = (
                        f"{timeout_info}No specific error recorded. "
                        f"Requires manual intervention."
                    )

                # State transition from PROCESSING to FAILED is valid,
                # no bypass needed
                email.status = EmailStatus.FAILED.value
                email.error_message = combined_error
                email.save(update_fields=["status", "error_message"])

                processing_failed_count += 1

        total_handled = (
            fetched_retry_count
            + fetched_failed_count
            + processing_failed_count
        )

        if total_handled > 0:
            logger.info(
                f"Handled {total_handled} stuck emails: "
                f"{fetched_retry_count} FETCHED retried, "
                f"{fetched_failed_count} FETCHED failed, "
                f"{processing_failed_count} PROCESSING failed"
            )
        tracer.append_task(
            "CLEANUP_COMPLETE",
            "Stuck email reset finished",
            {
                "fetched_retry_count": fetched_retry_count,
                "fetched_failed_count": fetched_failed_count,
                "processing_failed_count": processing_failed_count,
                "total_handled": total_handled,
                "completed_at": timezone.now().isoformat(),
            },
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
        tracer.append_task(
            "CLEANUP_ERROR",
            f"Stuck email reset failed: {exc}",
            {"error": str(exc)},
        )
        tracer.fail_task({"error": str(exc)}, str(exc))
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
@prevent_duplicate_task("email_task_cleanup", timeout=30)
def schedule_email_task_cleanup():
    """
    EmailTask records cleanup scheduler

    This task schedules the cleanup of old EmailTask records.
    It runs independently of the main email processing workflow.
    """
    tracer = TaskTracer(
        "TASK_CLEANUP",
        module="threadline",
    )
    try:
        with use_task_tracer(tracer):
            logger.info(
                f"{tracer.context_summary()} Starting EmailTask cleanup scheduler"
            )
            task_cleanup_manager = EmailTaskCleanupManager()
            result = task_cleanup_manager.cleanup_email_tasks()

        logger.info(
            f"{tracer.context_summary()} EmailTask cleanup completed: {result}"
        )
        return result

    except Exception as exc:
        tracer.fail_task({"error": str(exc)}, str(exc))
        logger.error(
            f"{tracer.context_summary()} EmailTask cleanup scheduling failed: {exc}"
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
