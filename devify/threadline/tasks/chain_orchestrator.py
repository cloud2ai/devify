"""
Chain Orchestrator for Email Processing Workflow

This module orchestrates the complete email processing chain:
1. OCR processing for image attachments
2. LLM processing for attachments OCR
3. LLM processing for email body
4. Email summarization
5. JIRA issue creation

The chain ensures proper sequencing and error handling.
"""

import logging

from celery import shared_task, chain

from threadline.models import EmailMessage
from threadline.tasks.ocr import ocr_images_for_email
from threadline.tasks.llm_email import llm_email_task
from threadline.tasks.llm_attachment import llm_ocr_task
from threadline.tasks.llm_summary import summarize_email_task
from threadline.tasks.issue import create_issue_task

logger = logging.getLogger(__name__)


@shared_task
def process_email_chain(
    email_id: str, force: bool = False
) -> str:
    """
    Main orchestrator task that creates the complete email processing chain.

    This task creates a chain of all processing steps:
    1. OCR processing for image attachments
    2. Attachments OCR organization using LLM
    3. Email body organization using LLM
    4. Email summarization using LLM (after email and attachment processing)
    5. JIRA issue creation (after all content is ready)

    STATE MACHINE FLOW
    ==================

    FETCHED → OCR_PROCESSING → OCR_SUCCESS
                    ↓
            LLM_OCR_PROCESSING → LLM_OCR_SUCCESS
                    ↓
            LLM_EMAIL_PROCESSING → LLM_EMAIL_SUCCESS
                    ↓
            LLM_SUMMARY_PROCESSING → LLM_SUMMARY_SUCCESS
                    ↓
            ISSUE_PROCESSING → ISSUE_SUCCESS → COMPLETED

    TASK EXECUTION ORDER
    ====================

    1. OCR Task: Processes image attachments for text extraction
    2. LLM Attachments Task: Organizes OCR content using LLM
    3. LLM Email Task: Processes email body content using LLM
    4. LLM Summary Task: Generates summary from all processed content
    5. Issue Task: Creates JIRA issue or marks as completed

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
        email = EmailMessage.objects.get(id=email_id)
        if not email:
            raise Exception(
                f"Email with id {email_id} not found")

        logger.info(f"[Chain] Starting processing chain for email: "
                    f"{email_id}, force: {force}")

        # Create the processing chain with sequential execution
        # Note: Using .si() (immutable signature) to pass force parameter
        processing_chain = chain(
            # Step 1: OCR processing (required first)
            ocr_images_for_email.si(email_id, force),

            # Step 2: Attachments OCR organization using LLM
            llm_ocr_task.si(email_id, force),

            # Step 3: Email body organization using LLM
            llm_email_task.si(email_id, force),

            # Step 4: Summarization (needs both email and attachment content)
            summarize_email_task.si(email_id, force),

            # Step 5: Issue creation (needs all content)
            create_issue_task.si(email_id, force)
        )

        # Execute the chain
        result = processing_chain.apply_async()
        logger.info(
            f"[Chain] Processing chain started for email: {email_id}, "
            f"current email status: {email.status}, force: {force}, "
            f"chain_task_id: {result.id}"
        )

        # Log the chain composition for debugging
        logger.debug(
            f"[Chain] Chain composition for email {email_id}: "
            f"OCR -> LLM Attachments OCR -> LLM Email Body -> "
            f"LLM Summary -> Issue Creation"
        )

        return email_id

    except Exception as exc:
        logger.error(f"[Chain] Failed to start processing chain "
                     f"for {email_id}: {exc}")
        raise
