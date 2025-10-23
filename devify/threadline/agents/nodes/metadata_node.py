"""
Metadata extraction node for email processing.

This node generates structured metadata for emails using LLM.
It operates purely on State without database access.
"""

import logging
from typing import Dict, Any

from threadline.agents.nodes.base_node import BaseLangGraphNode
from threadline.agents.email_state import EmailState, add_node_error
from threadline.utils.llm import call_llm

logger = logging.getLogger(__name__)


class MetadataNode(BaseLangGraphNode):
    """
    Metadata extraction node.

    This node generates structured metadata for emails by analyzing
    the summary title and content using LLM with JSON response format.

    State Input Requirements:
    - summary_title: Email summary title (from summary_node)
    - summary_content: Email summary content (from summary_node)
    - prompt_config: User's prompt configuration (from workflow_prepare)

    Responsibilities:
    - Check for summary_title and summary_content in State
    - Read prompt configuration from State (no database access)
    - Combine summary information for metadata extraction
    - Execute LLM processing to generate structured metadata
    - Validate JSON structure (category, scene, keywords, participants, timeline)
    - Update State with metadata
    - Skip if metadata already exists (unless force mode)
    - Handle LLM errors gracefully with retries
    """

    def __init__(self):
        super().__init__("metadata_node")

    def can_enter_node(self, state: EmailState) -> bool:
        """
        Check if Metadata node can enter.

        Metadata node can enter if:
        - No errors in previous nodes (or force mode)
        - Has summary_title and summary_content to analyze

        Args:
            state (EmailState): Current email state

        Returns:
            bool: True if node can enter, False otherwise
        """
        if not super().can_enter_node(state):
            return False

        force = state.get('force', False)
        summary_title = state.get('summary_title', '').strip()
        summary_content = state.get('summary_content', '').strip()

        if not force and (not summary_title or not summary_content):
            logger.error(
                "No summary_title or summary_content available for "
                "metadata extraction"
            )
            return False

        return True

    def execute_processing(self, state: EmailState) -> EmailState:
        """
        Execute metadata extraction.

        Analyzes summary title and content to generate structured metadata
        including category, scene, keywords, participants, and timeline.

        Args:
            state (EmailState): Current email state

        Returns:
            EmailState: Updated state with metadata results
        """
        force = state.get('force', False)

        prompt_config = state.get('prompt_config')
        if not prompt_config:
            error_message = 'No prompt_config found in State'
            logger.error(error_message)
            return add_node_error(state, self.node_name, error_message)

        metadata_prompt = prompt_config.get('metadata_prompt')
        if not metadata_prompt:
            error_message = 'Missing metadata_prompt in prompt_config'
            logger.error(error_message)
            return add_node_error(state, self.node_name, error_message)

        # Prepare content for metadata extraction
        summary_title = state.get('summary_title', '')
        summary_content = state.get('summary_content', '')
        subject = state.get('subject', '')

        content = (
            f"Email Subject: {subject}\n"
            f"Summary Title: {summary_title}\n"
            f"Summary Content:\n{summary_content}\n"
        )

        existing_metadata = state.get('metadata')

        try:
            if not existing_metadata or force:
                logger.info("Generating metadata from summary")

                # Call LLM with JSON response format and retry logic
                metadata = call_llm(
                    metadata_prompt,
                    content,
                    json_mode=True,
                    max_retries=3
                )

                # Validate required fields
                required_fields = [
                    'category',
                    'scene',
                    'keywords',
                    'participants',
                    'timeline'
                ]
                missing_fields = [
                    field for field in required_fields
                    if field not in metadata
                ]

                if missing_fields:
                    error_message = (
                        f"Metadata JSON missing required fields: "
                        f"{missing_fields}"
                    )
                    logger.error(error_message)
                    return add_node_error(
                        state,
                        self.node_name,
                        error_message
                    )

                # Ensure keywords, participants, and timeline are lists
                if not isinstance(metadata.get('keywords'), list):
                    metadata['keywords'] = []
                if not isinstance(metadata.get('participants'), list):
                    metadata['participants'] = []
                if not isinstance(metadata.get('timeline'), list):
                    metadata['timeline'] = []

                logger.info(
                    f"Metadata generated successfully with "
                    f"{len(metadata.get('keywords', []))} keywords, "
                    f"{len(metadata.get('participants', []))} participants"
                )

                return {
                    **state,
                    'metadata': metadata
                }
            else:
                logger.info(
                    "Metadata already exists and force mode is disabled, "
                    "skipping extraction"
                )
                return state

        except Exception as e:
            logger.error(f"Metadata extraction failed: {e}", exc_info=True)
            error_message = f'Metadata extraction failed: {str(e)}'
            return add_node_error(
                state,
                self.node_name,
                error_message
            )
