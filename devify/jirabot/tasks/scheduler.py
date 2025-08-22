import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

from ..models import EmailMessage
from ..state_machine import EmailStatus
from .chain_orchestrator import process_email_chain

logger = logging.getLogger(__name__)


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
    Scan and reset emails stuck in PROCESSING states for over timeout_minutes.

    This task identifies emails that have been stuck in processing states
    for longer than the specified timeout and resets them to appropriate
    previous states for retry.

    Args:
        timeout_minutes (int): Minutes after which emails are considered stuck
    """
    now = timezone.now()

    # Handle stuck OCR_PROCESSING
    stuck_ocr_emails = EmailMessage.objects.filter(
        status=EmailStatus.OCR_PROCESSING.value,
        updated_at__lt=now - timedelta(minutes=timeout_minutes)
    )
    for email in stuck_ocr_emails:
        logger.warning(
            f"Email {email.id} stuck in OCR_PROCESSING for "
            f"{timeout_minutes}+ minutes, resetting to FETCHED"
        )
        email.status = EmailStatus.FETCHED.value
        email.save(update_fields=['status'])

    # Handle stuck SUMMARY_PROCESSING
    stuck_summary_emails = EmailMessage.objects.filter(
        status=EmailStatus.SUMMARY_PROCESSING.value,
        updated_at__lt=now - timedelta(minutes=timeout_minutes)
    )
    for email in stuck_summary_emails:
        logger.warning(
            f"Email {email.id} stuck in SUMMARY_PROCESSING for "
            f"{timeout_minutes}+ minutes, resetting to OCR_SUCCESS"
        )
        email.status = EmailStatus.OCR_SUCCESS.value
        email.save(update_fields=['status'])

    # Handle stuck JIRA_PROCESSING
    stuck_jira_emails = EmailMessage.objects.filter(
        status=EmailStatus.JIRA_PROCESSING.value,
        updated_at__lt=now - timedelta(minutes=timeout_minutes)
    )
    for email in stuck_jira_emails:
        logger.warning(
            f"Email {email.id} stuck in JIRA_PROCESSING for "
            f"{timeout_minutes}+ minutes, resetting to SUMMARY_SUCCESS"
        )
        email.status = EmailStatus.SUMMARY_SUCCESS.value
        email.save(update_fields=['status'])

    # Log summary if any emails were reset
    total_reset = (len(stuck_ocr_emails) +
                   len(stuck_summary_emails) +
                   len(stuck_jira_emails))

    if total_reset > 0:
        logger.info(
            f"Reset {total_reset} stuck emails: "
            f"{len(stuck_ocr_emails)} OCR, "
            f"{len(stuck_summary_emails)} Summary, "
            f"{len(stuck_jira_emails)} JIRA"
        )