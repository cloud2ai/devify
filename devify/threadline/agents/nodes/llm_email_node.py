"""
LLM Email processing node for email content.

This node processes email text content using LLM to extract structured
information. It operates purely on State without database access.
"""

import logging
import re
from typing import Dict, Any

from threadline.agents.nodes.base_node import BaseLangGraphNode
from threadline.agents.email_state import EmailState, add_node_error
from threadline.utils.llm import call_llm

logger = logging.getLogger(__name__)


class LLMEmailNode(BaseLangGraphNode):
    """
    LLM Email processing node.

    This node processes email text content using LLM
    to extract and organize structured information.

    State Input Requirements:
    - text_content: Email text content to process
    - prompt_config: User's prompt configuration (from workflow_prepare)
    - attachments: List of attachment data with OCR content

    Responsibilities:
    - Check for email text content in State
    - Read prompt configuration from State (no database access)
    - Replace image placeholders with LLM-processed OCR content
    - Execute LLM processing on email content
    - Update State with llm_content
    - Skip if email already has LLM content (unless force mode)
    - Handle LLM errors gracefully
    """

    def __init__(self):
        super().__init__("llm_email_node")

    def can_enter_node(self, state: EmailState) -> bool:
        """
        Check if LLM Email node can enter.

        LLM Email node can enter if:
        - No errors in previous nodes (or force mode)
        - Has email text content to process

        Args:
            state (EmailState): Current email state

        Returns:
            bool: True if node can enter, False otherwise
        """
        if not super().can_enter_node(state):
            return False

        text_content = state.get('text_content', '').strip()
        if not text_content:
            logger.error(
                "No email text content available for LLM processing"
            )
            return False

        return True

    def execute_processing(self, state: EmailState) -> EmailState:
        """
        Execute LLM processing on email content.

        Reads email content from State, replaces image placeholders with
        OCR content, performs LLM processing, and updates State with
        LLM results.

        Args:
            state (EmailState): Current email state

        Returns:
            EmailState: Updated state with LLM results
        """
        force = state.get('force', False)
        text_content = state.get('text_content', '')
        llm_content = state.get('llm_content', '')

        if not force and llm_content:
            logger.info(
                f"Email already has LLM content, skipping in normal mode"
            )
            return state

        content_with_ocr = self._replace_image_placeholders_with_ocr(
            text_content,
            state.get('attachments', [])
        )

        prompt_config = state.get('prompt_config')
        if not prompt_config:
            error_message = 'No prompt_config found in State'
            logger.error(error_message)
            return add_node_error(state, self.node_name, error_message)

        email_content_prompt = prompt_config.get('email_content_prompt')
        if not email_content_prompt:
            error_message = 'Missing email_content_prompt in prompt_config'
            logger.error(error_message)
            return add_node_error(state, self.node_name, error_message)

        try:
            logger.info("Processing email content with LLM")

            logger.debug(f"Before LLM call: {content_with_ocr}")
            llm_result = call_llm(
                email_content_prompt,
                content_with_ocr
            )
            logger.debug(f"After LLM call: {llm_result}")
            llm_content = llm_result.strip() if llm_result else ''

            if llm_content:
                logger.info("LLM email processing successful")
                return {
                    **state,
                    'llm_content': llm_content
                }
            else:
                logger.warning(
                    "LLM email processing completed - no content generated"
                )
                return {
                    **state,
                    'llm_content': ''
                }

        except Exception as e:
            logger.exception(e)
            logger.error(f"LLM email processing failed: {e}")
            error_message = f'LLM email processing failed: {str(e)}'
            updated_state = add_node_error(
                state,
                self.node_name,
                error_message
            )
            updated_state['llm_content'] = ''
            return updated_state

    def _replace_image_placeholders_with_ocr(
        self,
        content: str,
        attachments: list
    ) -> str:
        """
        Replace [IMAGE: filename] placeholders with actual OCR content.

        This method finds all image placeholders in the content and replaces
        them with the corresponding LLM-processed OCR content from attachments.

        Args:
            content: Email content with image placeholders
            attachments: List of attachment states

        Returns:
            str: Content with image placeholders replaced by OCR content
        """
        image_placeholder_pattern = r'\[IMAGE:\s*([^\]]+)\]'
        placeholders = re.findall(image_placeholder_pattern, content)

        if not placeholders:
            logger.debug("No image placeholders found in email content")
            return content

        logger.info(
            f"Found {len(placeholders)} image placeholders: {placeholders}"
        )

        ocr_content_map = {}
        for att in attachments:
            # Only process image attachments
            if not att.get('is_image'):
                continue

            filename = att.get('filename')
            logger.debug(f"Processing image attachment: {filename}")

            # Get llm_content and check if it exists
            llm_content_raw = att.get('llm_content')
            if llm_content_raw:
                llm_content = llm_content_raw.strip()
            else:
                logger.debug(
                    f"No LLM content for {filename}, skipping"
                )
                continue

            safe_filename = att.get('safe_filename') or filename
            if safe_filename:
                ocr_content_map[safe_filename] = llm_content
                logger.debug(
                    f"Mapped {safe_filename} to OCR content "
                    f"({len(llm_content)} chars)"
                )

        logger.info(
            f"Created OCR content map with {len(ocr_content_map)} entries"
        )

        # Add OCR content as context without removing placeholders
        # This allows LLM to understand image content while
        # preserving placeholders for later processing
        replaced_count = 0
        for filename in placeholders:
            filename_stripped = filename.strip()
            if filename_stripped in ocr_content_map:
                placeholder = f"[IMAGE: {filename}]"
                ocr_content = ocr_content_map[filename_stripped]

                # Add OCR content AFTER the placeholder with clear delimiters
                # This keeps the placeholder for Jira processing
                content = content.replace(
                    placeholder,
                    f"{placeholder}\n"
                    f"--- OCR Content for {filename_stripped} ---\n"
                    f"{ocr_content}\n"
                    f"--- End of OCR Content ---\n"
                )
                replaced_count += 1
                logger.debug(
                    f"Added OCR content for {filename_stripped}"
                )
            else:
                logger.warning(
                    f"No OCR content found for image placeholder: "
                    f"{filename_stripped}"
                )

        logger.info(
            f"Replaced {replaced_count}/{len(placeholders)} image placeholders"
        )

        return content
