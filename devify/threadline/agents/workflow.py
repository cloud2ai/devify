"""
Email processing workflow using LangGraph StateGraph.

This module implements a sequential workflow for processing emails through
OCR, LLM processing, summarization, and issue creation using LangGraph.
"""

import logging
from functools import lru_cache
import traceback
from typing import Dict, Any

from langgraph.graph import StateGraph, START, END

from threadline.models import EmailMessage, EmailStatus
from threadline.agents.checkpoint_manager import create_checkpointer
from threadline.agents.nodes.workflow_prepare import WorkflowPrepareNode
from threadline.agents.nodes.workflow_finalize import WorkflowFinalizeNode
from threadline.agents.nodes.ocr_node import OCRNode
from threadline.agents.nodes.llm_attachment_node import LLMAttachmentNode
from threadline.agents.nodes.llm_email_node import LLMEmailNode
from threadline.agents.nodes.summary_node import SummaryNode
from threadline.agents.nodes.issue_node import IssueNode
from threadline.agents.email_state import (
    EmailState,
    create_email_state,
    has_node_errors
)

logger = logging.getLogger(__name__)


def _update_email_status_on_fatal_error(
    email_id: str,
    error_message: str
) -> None:
    """
    Update email status when workflow fails fatally.

    This is only called when WorkflowFinalizeNode won't execute
    (e.g., graph creation fails). In normal cases, status updates
    are handled by WorkflowFinalizeNode.

    Args:
        email_id: Email ID
        error_message: Error message to save
    """
    try:
        email = EmailMessage.objects.get(id=email_id)

        if email.status == EmailStatus.FETCHED.value:
            email.status = EmailStatus.PROCESSING.value
            email.save(update_fields=['status'])
            logger.info(
                f"Updated email status to PROCESSING for "
                f"email_id: {email_id}"
            )
            email.refresh_from_db()

        email.status = EmailStatus.FAILED.value
        email.error_message = error_message
        email.save(update_fields=['status', 'error_message'])
        logger.info(
            f"Updated email status to FAILED for email_id: {email_id}"
        )
    except Exception as update_error:
        logger.error(
            f"Failed to update email status for {email_id}: "
            f"{update_error}"
        )


@lru_cache(maxsize=1)
def create_email_processing_graph():
    """
    Create and compile the email processing workflow graph.

    Workflow sequence:
    1. WorkflowPrepareNode - Load email data and validate
    2. OCRNode - Process image attachments with OCR
    3. LLMAttachmentNode - Process OCR content with LLM
    4. LLMEmailNode - Process email content with LLM
    5. SummaryNode - Generate email summary
    6. IssueNode - Validate and prepare issue creation
    7. WorkflowFinalizeNode - Sync all results to database

    Returns:
        Compiled LangGraph workflow
    """
    logger.info("Building email processing workflow graph")

    workflow = StateGraph(EmailState)

    workflow.add_node("workflow_prepare", WorkflowPrepareNode())
    workflow.add_node("ocr", OCRNode())
    workflow.add_node("llm_attachment", LLMAttachmentNode())
    workflow.add_node("llm_email", LLMEmailNode())
    workflow.add_node("summary", SummaryNode())
    workflow.add_node("issue", IssueNode())
    workflow.add_node("workflow_finalize", WorkflowFinalizeNode())

    workflow.add_edge(START, "workflow_prepare")

    workflow.add_edge("workflow_prepare", "ocr")
    workflow.add_edge("ocr", "llm_attachment")
    workflow.add_edge("llm_attachment", "llm_email")
    workflow.add_edge("llm_email", "summary")
    workflow.add_edge("summary", "issue")
    workflow.add_edge("issue", "workflow_finalize")
    workflow.add_edge("workflow_finalize", END)

    graph = workflow.compile(checkpointer=create_checkpointer())

    logger.info("Email processing workflow graph compiled successfully")
    return graph


def execute_email_processing_workflow(
    email: EmailMessage,
    force: bool = False
) -> Dict[str, Any]:
    """
    Execute the email processing workflow for an email.

    Workflow Responsibilities:
    - This function orchestrates the graph execution
    - Status updates are handled by WorkflowFinalizeNode when graph executes
    - Only handles status for fatal errors (graph creation/execution fails)

    Args:
        email: EmailMessage object to process
        force: Whether to force execution even if already completed

    Returns:
        Dict with success status and result/error
    """
    email_id = email.id

    logger.info(
        f"Starting email workflow for email: {email_id}, "
        f"force: {force}, status: {email.status}"
    )

    try:
        initial_state = create_email_state(
            email_id,
            str(email.user_id),
            force
        )

        graph = create_email_processing_graph()

        config = {
            "configurable": {
                "thread_id": f"email_workflow_{email_id}",
                "checkpoint_ns": "email_processing"
            }
        }
        result = graph.invoke(initial_state, config=config)

        logger.info(f"Email workflow result: {result}")

        success = not has_node_errors(result)

        if success:
            logger.info(
                f"Email workflow completed successfully: {email_id}"
            )
        else:
            node_errors = result.get('node_errors', {})
            logger.error(
                f"Email workflow completed with errors: {email_id}, "
                f"errors: {node_errors}"
            )

        return {
            'success': success,
            'result': result,
            'error': (
                f'Email workflow failed with errors: '
                f'{result.get("node_errors", {})}'
                if not success else None
            )
        }

    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(
            f"Fatal workflow error for email {email_id}: {e}"
        )
        logger.error(f"Full traceback:\n{error_traceback}")

        error_msg = str(e)
        _update_email_status_on_fatal_error(email_id, error_msg)

        return {
            'success': False,
            'result': None,
            'error': error_msg
        }


def get_email_workflow_status(email_id: str) -> Dict[str, Any]:
    """
    Get the current status of a workflow for an email.

    Args:
        email_id: ID of the email

    Returns:
        Dict with workflow status information
    """
    try:
        graph = create_email_processing_graph()

        return {
            'email_id': email_id,
            'status': 'unknown',
            'message': 'Workflow status check not fully implemented'
        }
    except Exception as e:
        logger.error(f"Error getting email workflow status: {email_id}, {e}")
        return {
            'email_id': email_id,
            'status': 'error',
            'error': str(e)
        }


def clear_email_workflow_checkpoint(email_id: str) -> bool:
    """
    Clear workflow checkpoint for an email.

    Args:
        email_id: ID of the email

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info(f"Clearing email workflow checkpoint for: {email_id}")
        return True
    except Exception as e:
        logger.error(
            f"Error clearing email workflow checkpoint: {email_id}, {e}"
        )
        return False
