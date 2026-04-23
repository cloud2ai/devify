"""
LangGraph Agents for Email Processing

This module contains the LangGraph agent implementations for the email
processing pipeline. These agents use a three-phase processing structure and
state-driven design for clean separation of concerns.

Agents:
- workflow_prepare: Initial validation and state preparation
- image_intent_node: Multimodal image understanding for attachments
- llm_attachment_node: LLM processing for attachment insights
- llm_email_node: LLM processing for email content
- summary_node: Email summarization
- metadata_node: Metadata extraction
- issue_node: Issue creation validation and preparation
- workflow_finalize: Final database synchronization and status updates

State Management:
- EmailState: Main state structure for LangGraph workflow
- NodeError: Structured error tracking per node
"""

from threadline.agents.nodes.base_node import BaseLangGraphNode
from threadline.agents.workflow import (
    execute_email_processing_workflow,
    get_email_workflow_status,
    clear_email_workflow_checkpoint,
)
from threadline.agents.email_state import (
    EmailState,
    NodeError,
    create_email_state,
    add_node_error,
    has_node_errors,
    get_node_errors_by_name,
    clear_node_errors_by_name,
    get_all_node_names_with_errors,
)

__all__ = [
    "BaseLangGraphNode",
    "execute_email_processing_workflow",
    "get_email_workflow_status",
    "clear_email_workflow_checkpoint",
    "EmailState",
    "NodeError",
    "create_email_state",
    "add_node_error",
    "has_node_errors",
    "get_node_errors_by_name",
    "clear_node_errors_by_name",
    "get_all_node_names_with_errors",
]
