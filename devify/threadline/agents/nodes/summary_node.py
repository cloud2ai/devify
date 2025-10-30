"""
Summary generation node for email processing.

This node generates summary content and title for the email using LLM.
It operates purely on State without database access.
"""

import logging
from typing import Dict, Any

from threadline.agents.nodes.base_node import BaseLangGraphNode
from threadline.agents.email_state import EmailState, add_node_error
from threadline.utils.llm import call_llm

logger = logging.getLogger(__name__)


class SummaryNode(BaseLangGraphNode):
    """
    Summary generation node.

    This node generates summary content and title for the email
    based on the LLM-processed email content.

    State Input Requirements:
    - llm_content: Email content processed by LLM (includes OCR context)
    - prompt_config: User's prompt configuration (from workflow_prepare)
    - subject: Email subject

    Responsibilities:
    - Check for email LLM content in State
    - Read prompt configuration from State (no database access)
    - Execute LLM processing to generate summary content and title
    - Update State with summary_content and summary_title
    - Skip if summary already exists (unless force mode)
    - Handle LLM errors gracefully
    """

    def __init__(self):
        super().__init__("summary_node")

    def can_enter_node(self, state: EmailState) -> bool:
        """
        Check if Summary node can enter.

        Summary node can enter if:
        - No errors in previous nodes (or force mode)
        - Has email LLM content to summarize

        Args:
            state (EmailState): Current email state

        Returns:
            bool: True if node can enter, False otherwise
        """
        if not super().can_enter_node(state):
            return False

        force = state.get('force', False)
        llm_content_raw = state.get('llm_content', '')
        llm_content = llm_content_raw.strip() if llm_content_raw else ''

        if not force and not llm_content:
            logger.error(
                "No email LLM content available for summary generation"
            )
            return False

        return True

    def execute_processing(self, state: EmailState) -> EmailState:
        """
        Execute summary generation.

        Generates summary content and title based on LLM-processed email
        content (which already includes OCR context from attachments).

        Args:
            state (EmailState): Current email state

        Returns:
            EmailState: Updated state with summary results
        """
        force = state.get('force', False)

        prompt_config = state.get('prompt_config')
        if not prompt_config:
            error_message = 'No prompt_config found in State'
            logger.error(error_message)
            return add_node_error(state, self.node_name, error_message)

        summary_prompt = prompt_config.get('summary_prompt')
        summary_title_prompt = prompt_config.get('summary_title_prompt')
        if not summary_prompt or not summary_title_prompt:
            error_message = (
                'Missing summary_prompt or summary_title_prompt in '
                'prompt_config'
            )
            logger.error(error_message)
            return add_node_error(state, self.node_name, error_message)

        # Build content with subject and LLM-processed email content
        # Note: llm_content already includes OCR context from attachments
        content = (
            f"Subject: {state.get('subject', '')}\n"
            f"Text Content: {state.get('llm_content', '')}\n"
        )

        logger.info("Using LLM-processed content for summary generation")

        summary_content = state.get('summary_content', '')
        summary_title = state.get('summary_title', '')

        try:
            if not summary_content or force:
                logger.info("Generating summary content")
                summary_content_raw = call_llm(
                    summary_prompt,
                    content
                )
                if summary_content_raw:
                    summary_content = summary_content_raw.strip()
                else:
                    summary_content = ''
                if summary_content:
                    logger.info("Summary content generated successfully")
                else:
                    logger.warning("No summary content generated")

            if not summary_title or force:
                logger.info("Generating summary title")
                summary_title_raw = call_llm(
                    summary_title_prompt,
                    content
                )
                if summary_title_raw:
                    summary_title = summary_title_raw.strip()
                else:
                    summary_title = ''
                if summary_title:
                    logger.info("Summary title generated successfully")
                else:
                    logger.warning("No summary title generated")

            return {
                **state,
                'summary_content': summary_content,
                'summary_title': summary_title
            }

        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            error_message = f'Summary generation failed: {str(e)}'
            updated_state = add_node_error(
                state,
                self.node_name,
                error_message
            )
            updated_state['summary_content'] = summary_content or ''
            updated_state['summary_title'] = summary_title or ''
            return updated_state
