import logging
from celery import shared_task
from ..models import EmailMessage
from .ocr import ocr_images_for_email
from .summary import llm_process_email
from .jira import submit_issue_to_jira

logger = logging.getLogger(__name__)

@shared_task
def schedule_email_processing_tasks():
    """
    Unified scheduler for driving email processing tasks based on status.
    """
    # Schedule OCR for emails that have been fetched but not yet OCR'd
    for email in EmailMessage.objects.filter(
        status=EmailMessage.ProcessingStatus.FETCHED
    ):
        logger.info(
            f"Scheduling OCR for email id={email.id}, "
            f"subject={email.subject}"
        )
        ocr_images_for_email.delay(email.id)

    # Schedule summary for emails that have completed OCR
    for email in EmailMessage.objects.filter(
        status=EmailMessage.ProcessingStatus.OCR_SUCCESS
    ):
        logger.info(
            f"Scheduling summary for email id={email.id}, "
            f"subject={email.subject}"
        )
        llm_process_email.delay(email.id)

    # Schedule JIRA issue creation for emails that have completed summary
    for email in EmailMessage.objects.filter(
        status=EmailMessage.ProcessingStatus.SUMMARY_SUCCESS
    ):
        logger.info(
            f"Scheduling JIRA issue creation for email id={email.id}, "
            f"subject={email.subject}"
        )
        submit_issue_to_jira.delay(email.id)