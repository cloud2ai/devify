"""
Email Workflow Tasks

This module provides Celery task wrappers for the LangGraph-based
email processing workflow. It replaces the chain-based approach with
a unified state graph execution.

Workflow Architecture:
- Single workflow execution (no Celery chains)
- Unified state management via LangGraph
- Atomic database operations in prepare/finalize nodes
- Built-in checkpointing and error recovery

File: devify/threadline/tasks/email_workflow.py
"""

import logging
from celery import shared_task
from django.conf import settings

from threadline.models import EmailMessage
from threadline.agents.workflow import (
    execute_email_processing_workflow
)
from threadline.utils.task_lock import prevent_duplicate_task

logger = logging.getLogger(__name__)


@shared_task
@prevent_duplicate_task(
    "process_email_workflow",
    user_id_param="email_id",
    timeout=settings.TASK_TIMEOUT_MINUTES
)
def process_email_workflow(
    email_id: str,
    force: bool = False
) -> str:
    """
    Execute LangGraph-based email processing workflow.

    This task replaces the traditional Celery chain approach with a
    unified LangGraph StateGraph execution. The workflow manages all
    processing steps (OCR, LLM, Summary, Issue) in a single graph.

    Workflow Steps (executed by LangGraph):
    1. WorkflowPrepareNode - Load and validate email data
    2. OCRNode - Process image attachments
    3. LLMAttachmentNode - Process OCR content with LLM
    4. LLMEmailNode - Process email content with LLM
    5. SummaryNode - Generate email summary
    6. IssueNode - Validate and prepare issue creation
    7. WorkflowFinalizeNode - Sync all results to database

    State Machine Integration:
    - Prepare: Sets status to PROCESSING (unless force mode)
    - Finalize: Sets status to SUCCESS or FAILED based on workflow result
    - Force mode: Skips all status changes

    Args:
        email_id (str): ID of the email to process
        force (bool): Whether to force processing regardless of current
                     status. When True, bypasses status checks and allows
                     reprocessing even if content already exists.

    Returns:
        str: The email_id (for Celery chain compatibility)

    Raises:
        ValueError: If email not found
        Exception: For workflow execution errors
    """
    try:
        email = EmailMessage.objects.get(id=email_id)
        if not email:
            raise ValueError(f"Email with id {email_id} not found")

        logger.info(
            f"[Workflow] Starting LangGraph workflow for email: {email_id}, "
            f"force: {force}, current_status: {email.status}"
        )

        result = execute_email_processing_workflow(
            email=email,
            force=force
        )

        if result['success']:
            logger.info(
                f"[Workflow] Email processing completed successfully: "
                f"{email_id}"
            )
        else:
            logger.error(
                f"[Workflow] Email processing failed: {email_id}, "
                f"error: {result.get('error')}"
            )

        return email_id

    except EmailMessage.DoesNotExist:
        logger.error(f"[Workflow] EmailMessage {email_id} not found")
        raise ValueError(f"Email with id {email_id} not found")
    except Exception as exc:
        logger.error(
            f"[Workflow] Failed to execute workflow for {email_id}: {exc}"
        )
        raise


@shared_task
def retry_failed_email_workflow(
    email_id: str
) -> str:
    """
    Retry a failed email workflow.

    This is a convenience task that calls the workflow with force=True
    to retry processing from the beginning.

    Args:
        email_id (str): ID of the email to retry

    Returns:
        str: The email_id
    """
    logger.info(f"[Workflow] Retrying failed workflow for email: {email_id}")
    return process_email_workflow(email_id, force=True)
