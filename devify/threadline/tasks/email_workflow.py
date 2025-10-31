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
    lock_param="email_id",
    timeout=settings.TASK_TIMEOUT_MINUTES
)
def process_email_workflow(
    email_id: str,
    force: bool = False,
    language: str = None,
    scene: str = None
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
        language (str, optional): Language override for this processing
                                 (e.g., 'zh-CN', 'en-US'). If provided,
                                 will override user's default language
                                 for this retry only.
        scene (str, optional): Scene override for this processing
                              (e.g., 'chat', 'product_issue'). If provided,
                              will override user's default scene for this
                              retry only.

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

        user_info = f"{email.user.username}({email.user_id})"
        logger.info(
            f"[Workflow] Starting for email {email_id}, user {user_info}, "
            f"status: {email.status}, force: {force}, "
            f"language: {language}, scene: {scene}"
        )

        result = execute_email_processing_workflow(
            email=email,
            force=force,
            language=language,
            scene=scene
        )

        if result['success']:
            logger.info(
                f"[Workflow] Completed successfully for email {email_id}, "
                f"user {user_info}"
            )
        else:
            logger.error(
                f"[Workflow] Failed for email {email_id}, user {user_info}: "
                f"{result.get('error')}"
            )

        return email_id

    except EmailMessage.DoesNotExist:
        logger.error(
            f"[Workflow] EmailMessage {email_id} not found"
        )
        raise ValueError(f"Email with id {email_id} not found")
    except Exception as exc:
        logger.error(
            f"[Workflow] Failed to execute for email {email_id}: {exc}"
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
    logger.info(
        f"[Workflow] Retrying failed workflow for email {email_id}"
    )
    return process_email_workflow(email_id, force=True)
