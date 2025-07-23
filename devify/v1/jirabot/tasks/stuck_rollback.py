import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from ..models import EmailMessage

logger = logging.getLogger(__name__)

@shared_task
def reset_stuck_processing_emails(timeout_minutes=30):
    """
    Scan and reset emails stuck in PROCESSING states for over timeout_minutes.
    """
    now = timezone.now()
    # Handle stuck OCR_PROCESSING
    for email in EmailMessage.objects.filter(
        status=EmailMessage.ProcessingStatus.OCR_PROCESSING,
        updated_at__lt=now - timedelta(minutes=timeout_minutes)
    ):
        logger.warning(
            f"Email {email.id} stuck in OCR_PROCESSING, "
            f"resetting to FETCHED"
        )
        email.status = EmailMessage.ProcessingStatus.FETCHED
        email.save(update_fields=['status'])

    # Handle stuck SUMMARY_PROCESSING
    for email in EmailMessage.objects.filter(
        status=EmailMessage.ProcessingStatus.SUMMARY_PROCESSING,
        updated_at__lt=now - timedelta(minutes=timeout_minutes)
    ):
        logger.warning(
            f"Email {email.id} stuck in SUMMARY_PROCESSING, "
            f"resetting to OCR_SUCCESS"
        )
        email.status = EmailMessage.ProcessingStatus.OCR_SUCCESS
        email.save(update_fields=['status'])

    # Handle stuck JIRA_PROCESSING
    for email in EmailMessage.objects.filter(
        status=EmailMessage.ProcessingStatus.JIRA_PROCESSING,
        updated_at__lt=now - timedelta(minutes=timeout_minutes)
    ):
        logger.warning(
            f"Email {email.id} stuck in JIRA_PROCESSING, "
            f"resetting to SUMMARY_SUCCESS"
        )
        email.status = EmailMessage.ProcessingStatus.SUMMARY_SUCCESS
        email.save(update_fields=['status'])

    # Handle stuck ATTACHMENT_UPLOADING (if used)
    for email in EmailMessage.objects.filter(
        status=EmailMessage.ProcessingStatus.ATTACHMENT_UPLOADING,
        updated_at__lt=now - timedelta(minutes=timeout_minutes)
    ):
        logger.warning(
            f"Email {email.id} stuck in ATTACHMENT_UPLOADING, "
            f"resetting to JIRA_SUCCESS"
        )
        email.status = EmailMessage.ProcessingStatus.JIRA_SUCCESS
        email.save(update_fields=['status'])