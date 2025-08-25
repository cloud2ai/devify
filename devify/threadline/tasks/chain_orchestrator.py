"""
Chain Orchestrator for Email Processing Workflow

This module orchestrates the complete email processing chain:
1. OCR processing for image attachments
2. LLM processing for email content and attachments
3. JIRA issue creation

The chain ensures proper sequencing and error handling.
"""

import logging

from celery import shared_task, chain

from threadline.models import EmailMessage
from threadline.tasks.ocr import ocr_images_for_email
from threadline.tasks.jira import submit_issue_to_jira
from threadline.tasks.llm_email import organize_email_body_task
from threadline.tasks.llm_attachment import organize_attachments_ocr_task
from threadline.tasks.llm_summary import summarize_email_task

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def process_email_chain(
    self, email_id: str, force: bool = False
) -> str:
    """
    Main orchestrator task that creates the complete email processing chain.

    This task creates a chain of all processing steps:
    1. OCR processing for image attachments
    2. Attachments OCR organization using LLM (immediately after OCR)
    3. Email body organization using LLM
    4. Email summarization using LLM
    5. JIRA issue creation

    Args:
        email_id (str): ID of the email to process
        force (bool): Whether to force processing regardless of current status.
                     When True, skips status checks and allows reprocessing
                     even if the content already exists.

    Returns:
        str: The email_id for the next task in the chain
    """
    try:
        # Validate that the email exists
        if not EmailMessage.objects.filter(id=email_id).exists():
            raise EmailMessage.DoesNotExist(
                f"Email with id {email_id} not found")

        logger.info(f"[Chain] Starting processing chain for email: {email_id}")

        # Create the processing chain
        processing_chain = chain(
            ocr_images_for_email.s(email_id, force),
            organize_attachments_ocr_task.s(email_id, force),
            organize_email_body_task.s(email_id, force),
            summarize_email_task.s(email_id, force),
            submit_issue_to_jira.s(email_id, force)
        )

        # Execute the chain
        result = processing_chain.apply_async()
        logger.info(
            f"[Chain] Processing chain started for email: {email_id}, "
            f"chain_task_id: {result.id}, initial_state: {result.state}"
        )

        # Log the chain composition for debugging
        logger.debug(
            f"[Chain] Chain composition for email {email_id}: "
            f"OCR -> Attachment OCR Organization -> Email Organization -> "
            f"Summarization -> JIRA Creation"
        )

        return email_id

    except Exception as exc:
        logger.error(f"[Chain] Failed to start processing chain "
                     f"for {email_id}: {exc}")
        raise
