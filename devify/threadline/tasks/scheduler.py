import logging
from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from threadline.models import EmailMessage
from threadline.state_machine import EmailStatus
from threadline.tasks.chain_orchestrator import process_email_chain
from threadline.tasks.email_fetch import imap_email_fetch, haraka_email_fetch
from threadline.tasks.cleanup import (EmailCleanupManager,
                                      EmailTaskCleanupManager)
from threadline.utils.task_cleanup import cleanup_stale_tasks
from threadline.utils.task_lock import prevent_duplicate_task
from django.conf import settings

logger = logging.getLogger(__name__)

# Configuration for stuck email handling
# Each item defines: (reset_to_status, description)
STUCK_STATUS_RESET_MAP = {
    # Processing states that might get stuck
    EmailStatus.OCR_PROCESSING.value: (
        EmailStatus.FETCHED.value,
        'OCR'
    ),
    EmailStatus.LLM_EMAIL_PROCESSING.value: (
        EmailStatus.FETCHED.value,
        'LLM_EMAIL'
    ),
    EmailStatus.LLM_SUMMARY_PROCESSING.value: (
        EmailStatus.FETCHED.value,
        'LLM_SUMMARY'
    ),
    EmailStatus.ISSUE_PROCESSING.value: (
        EmailStatus.FETCHED.value,
        'Issue'
    ),

    # Success states that might get stuck in chain
    # Reset all to FETCHED to restart the entire processing chain
    EmailStatus.OCR_SUCCESS.value: (
        EmailStatus.FETCHED.value,
        'OCR_SUCCESS'
    ),
    EmailStatus.LLM_EMAIL_SUCCESS.value: (
        EmailStatus.FETCHED.value,
        'LLM_EMAIL_SUCCESS'
    ),
    EmailStatus.LLM_SUMMARY_SUCCESS.value: (
        EmailStatus.FETCHED.value,
        'LLM_SUMMARY_SUCCESS'
    ),
    EmailStatus.ISSUE_SUCCESS.value: (
        EmailStatus.FETCHED.value,
        'ISSUE_SUCCESS'
    ),
}


@shared_task
@prevent_duplicate_task("email_fetch", timeout=settings.TASK_TIMEOUT_MINUTES)
def schedule_email_fetch():
    """
    Unified email fetch scheduler

    This is the main entry point for all email fetching operations.
    Schedules both IMAP and Haraka email fetch tasks.

    Responsibilities:
    1. Check task locks (handled by decorator)
    2. Clean up stale tasks
    3. Schedule both IMAP and Haraka email fetch tasks
    4. Task lock mechanism (TASK_TIMEOUT_MINUTES timeout)
    5. Error handling and monitoring
    """
    try:
        logger.info("Starting unified email fetch scheduling")

        # Check unclosed state machines
        cleanup_stale_tasks()

        # Schedule both email fetch tasks
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
def schedule_email_processing_tasks():
    """
    Unified scheduler for driving email processing tasks based on status.

    This scheduler now uses the new chain-based approach for better
    workflow management and error handling.
    """
    # Schedule complete processing chain for emails that are ready to start
    for email in EmailMessage.objects.filter(
        status=EmailStatus.FETCHED.value
    ):
        logger.info(
            f"Scheduling complete processing chain for email id={email.id}, "
            f"subject={email.subject}"
        )
        process_email_chain.delay(email.id)


@shared_task
def schedule_reset_stuck_processing_emails(timeout_minutes=30):
    """
    Scan and reset emails stuck in any state for over timeout_minutes.

    This task identifies emails that have been stuck in any processing
    or success state for longer than the specified timeout and resets
    them to FETCHED state to restart the entire processing chain.

    Args:
        timeout_minutes (int): Minutes after which emails are considered stuck
    """
    now = timezone.now()

    # Get all stuck emails in one query using 'in' operator
    stuck_statuses = list(STUCK_STATUS_RESET_MAP.keys())
    stuck_emails = EmailMessage.objects.filter(
        status__in=stuck_statuses,
        updated_at__lt=now - timedelta(minutes=timeout_minutes)
    )

    # Process each stuck email
    reset_results = {}
    for email in stuck_emails:
        reset_to_status, description = STUCK_STATUS_RESET_MAP[email.status]

        logger.warning(
            f"Email {email.id} stuck in {email.status} for "
            f"{timeout_minutes}+ minutes, resetting to {reset_to_status}"
        )

        # Save the old status for logging
        old_status = email.status

        # Update the email status and persist the change
        email.status = reset_to_status
        email.save(update_fields=['status'])

        # Log the status reset with controlled line length
        logger.info(
            "[Scheduler] Reset email %s from %s to %s",
            email.id,
            old_status,
            reset_to_status
        )

        # Count resets by description
        reset_results[description] = reset_results.get(description, 0) + 1

    # Log summary if any emails were reset
    total_reset = sum(reset_results.values())

    if total_reset > 0:
        logger.info(
            "Reset %d stuck emails: %s",
            total_reset,
            ", ".join(
                [
                    f"{count} {desc}"
                    for desc, count in reset_results.items()
                    if count > 0
                ]
            ),
        )


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
