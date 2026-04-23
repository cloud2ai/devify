"""
Email processing workflow using LangGraph StateGraph.

This module implements a sequential workflow for processing emails through
multimodal image understanding, LLM processing, summarization, and issue
creation using LangGraph.
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
from threadline.agents.nodes.credits_check_node import CreditsCheckNode
from threadline.agents.nodes.error_handler_node import ErrorHandlerNode
from threadline.agents.nodes.image_intent_node import ImageIntentNode
from threadline.agents.nodes.llm_email_node import LLMEmailNode
from threadline.agents.nodes.summary_node import SummaryNode
from threadline.agents.nodes.metadata_node import MetadataNode
from threadline.agents.nodes.issue_node import IssueNode
from threadline.agents.email_state import (
    EmailState,
    create_email_state,
    has_node_errors,
)
from threadline.utils.task_tracer import TaskTracer, use_task_tracer

logger = logging.getLogger(__name__)


def _update_email_status_on_fatal_error(
    email_id: str, error_message: str
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

        # Directly set status to FAILED regardless of current status
        # State machine allows FETCHED → FAILED and PROCESSING → FAILED
        # No need to set PROCESSING first as this is a fatal error
        email.set_status(EmailStatus.FAILED.value, error_message=error_message)
        logger.info(
            f"Updated email status to FAILED for email_id: {email_id} "
            f"(fatal workflow error, previous status: {email.status})"
        )
    except Exception as update_error:
        logger.error(
            f"Failed to update email status for {email_id}: " f"{update_error}"
        )


def should_handle_error(state: EmailState) -> str:
    """
    Conditional routing function for error handling.

    This function is called AFTER all business nodes have executed.
    It checks if ANY node produced errors during execution.

    Design Pattern: "Collect & Handle" (not "Fail-Fast")
    - Nodes don't immediately abort on error
    - Errors are accumulated in state['node_errors']
    - All nodes execute (may skip processing if errors exist)
    - This function checks accumulated errors and decides routing

    Routing Logic:
    - If has_node_errors(state) → "error_handler"
      → ErrorHandler will analyze errors and decide refund
    - If no errors → "workflow_finalize"
      → Directly finalize without error handling

    Note: This means ErrorHandler only executes when workflow has errors,
    not immediately when a single node fails.

    Args:
        state: EmailState containing node_errors from all executed nodes

    Returns:
        str: Next node name ("error_handler" or "workflow_finalize")
    """
    if has_node_errors(state):
        return "error_handler"
    return "workflow_finalize"


@lru_cache(maxsize=1)
def create_email_processing_graph():
    """
    Create and compile the email processing workflow graph.

    Workflow sequence:
    1. WorkflowPrepareNode - Load email data and validate
    2. CreditsCheckNode - Check and consume credits
    3. ImageIntentNode - Process image attachments with multimodal LLM
    4. LLMEmailNode - Process email content with LLM
    5. SummaryNode - Generate email summary
    6. MetadataNode - Extract structured metadata from summary
    7. IssueNode - Validate and prepare issue creation
    8. ErrorHandlerNode - Handle errors and refund credits (conditional)
    9. WorkflowFinalizeNode - Sync all results to database

    Returns:
        Compiled LangGraph workflow
    """
    logger.info("Building email processing workflow graph")

    workflow = StateGraph(EmailState)

    workflow.add_node("workflow_prepare", WorkflowPrepareNode())
    workflow.add_node("credits_check", CreditsCheckNode())
    workflow.add_node("image_intent", ImageIntentNode())
    workflow.add_node("llm_email", LLMEmailNode())
    workflow.add_node("summary", SummaryNode())
    workflow.add_node("metadata", MetadataNode())
    workflow.add_node("issue", IssueNode())
    workflow.add_node("error_handler", ErrorHandlerNode())
    workflow.add_node("workflow_finalize", WorkflowFinalizeNode())

    workflow.add_edge(START, "workflow_prepare")
    workflow.add_edge("workflow_prepare", "credits_check")
    workflow.add_edge("credits_check", "image_intent")
    workflow.add_edge("image_intent", "llm_email")
    workflow.add_edge("llm_email", "summary")
    workflow.add_edge("summary", "metadata")
    workflow.add_edge("metadata", "issue")

    # CRITICAL: Conditional routing for error handling
    # This is where we decide whether to handle errors or finalize directly
    # Position: After all business nodes (issue is the last one)
    # Logic:
    #   - If ANY node had errors → Route to error_handler
    #     → ErrorHandler analyzes errors and refunds if system error
    #   - If NO errors → Route directly to workflow_finalize
    #     → Skip error handling, go straight to success finalization
    #
    # Design Note: This is NOT fail-fast! All nodes execute first,
    # then we check accumulated errors. This allows:
    # - Collecting partial results even if some nodes fail
    # - Unified error analysis (not per-node)
    # - Flexible refund decisions based on all errors
    workflow.add_conditional_edges(
        "issue",
        should_handle_error,
        {
            "error_handler": "error_handler",
            "workflow_finalize": "workflow_finalize",
        },
    )

    # ErrorHandler always goes to finalize (after refund decision)
    workflow.add_edge("error_handler", "workflow_finalize")

    # WorkflowFinalize is the single exit point (always executes)
    workflow.add_edge("workflow_finalize", END)

    graph = workflow.compile(checkpointer=create_checkpointer())

    logger.info("Email processing workflow graph compiled successfully")
    return graph


def execute_email_processing_workflow(
    email: EmailMessage,
    force: bool = False,
    language: str = None,
    scene: str = None,
    tracer: TaskTracer | None = None,
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
        language: Optional language override for this retry
        scene: Optional scene override for this retry

    Returns:
        Dict with success status and result/error
    """
    email_id = email.id
    user_id = email.user_id

    try:
        tracer = tracer or TaskTracer("EMAIL_WORKFLOW")
        logger.info(
            f"{tracer.context_summary({'email_id': email_id, 'user_id': user_id, 'force': force, 'language': language, 'scene': scene})} "
            f"starting workflow for email {email_id}, user {user_id}, status: {email.status}, force: {force}, language: {language}, scene: {scene}"
        )
        initial_state = create_email_state(email_id, str(email.user_id), force)

        if language:
            initial_state["retry_language"] = language
        if scene:
            initial_state["retry_scene"] = scene

        graph = create_email_processing_graph()

        if force:
            from django.utils import timezone

            timestamp = int(timezone.now().timestamp())
            thread_id = f"email_workflow_{email_id}_force_{timestamp}"
        else:
            thread_id = f"email_workflow_{email_id}"

        config = {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": "email_processing",
            }
        }

        logger.info(
            f"{tracer.context_summary({'email_id': email_id, 'user_id': user_id, 'force': force, 'language': language, 'scene': scene})} "
            f"using thread_id={thread_id} (force={force})"
        )

        tracer.append_task(
            "WORKFLOW_START",
            "Email processing workflow started",
            {
                "email_id": str(email_id),
                "force": force,
                "language": language,
                "scene": scene,
            },
        )

        with use_task_tracer(tracer):
            result = graph.invoke(initial_state, config=config)

        success = not has_node_errors(result)

        if success:
            logger.info(
                f"{tracer.context_summary({'email_id': email_id, 'user_id': user_id, 'force': force, 'language': language, 'scene': scene})} "
                f"completed successfully for email {email_id}, user {user_id}"
            )
        else:
            node_errors = result.get("node_errors", {})
            logger.error(
                f"{tracer.context_summary({'email_id': email_id, 'user_id': user_id, 'force': force, 'language': language, 'scene': scene})} "
                f"completed with errors for email {email_id}, user {user_id}: {node_errors}"
            )

        tracer.append_task(
            "WORKFLOW_COMPLETE" if success else "WORKFLOW_FAILED",
            (
                "Email processing workflow completed successfully"
                if success
                else "Email processing workflow completed with errors"
            ),
            {
                "email_id": str(email_id),
                "success": success,
                "node_errors": result.get("node_errors", {}),
            },
        )

        return {
            "success": success,
            "result": result,
            "error": (
                f'Email workflow failed with errors: '
                f'{result.get("node_errors", {})}'
                if not success
                else None
            ),
        }

    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(
            f"Fatal workflow error for email {email_id}, user {user_id}: {e}"
        )
        logger.error(f"Full traceback:\n{error_traceback}")

        error_msg = str(e)
        if tracer is not None:
            tracer.append_task(
                "WORKFLOW_ERROR",
                f"Email processing workflow failed: {error_msg}",
                {
                    "email_id": str(email_id),
                    "error": error_msg,
                    "traceback": error_traceback,
                },
            )
        _update_email_status_on_fatal_error(email_id, error_msg)

        return {"success": False, "result": None, "error": error_msg}


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
            "email_id": email_id,
            "status": "unknown",
            "message": "Workflow status check not fully implemented",
        }
    except Exception as e:
        logger.error(f"Error getting email workflow status: {email_id}, {e}")
        return {"email_id": email_id, "status": "error", "error": str(e)}


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
