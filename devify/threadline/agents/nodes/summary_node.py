"""
Summary generation node for email processing.

This node generates summary content and title for the email using LLM.
It operates purely on State without database access.
"""

import logging
from typing import Any, Dict, List

from dateutil import parser as date_parser
from django.utils import timezone
from zoneinfo import ZoneInfo

from core.tracking import LLMTracker
from threadline.agents.email_state import EmailState, add_node_error
from threadline.agents.nodes.base_node import BaseLangGraphNode

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
    - Execute LLM processing to generate structured JSON
      (details, key_process, todo)
    - Process TODO items (time parsing, validation, fallback logic)
    - Update State with summary_data, todos, summary_content and
      summary_title
    - Skip if summary already exists (unless force mode)
    - Handle LLM errors gracefully

    Note: summary_content is only generated in fallback mode when JSON
    generation fails. For normal operation, use summary_data and todos
    directly. Markdown rendering should be handled at API layer if needed.
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

    def _process_todos(
        self,
        todos: List[Dict[str, Any]],
        received_at: str
    ) -> List[Dict[str, Any]]:
        """
        Process TODO items: validate and process time information.

        Args:
            todos: List of TODO items from LLM JSON response
            received_at: Email received time (ISO format string)

        Returns:
            List of processed TODO items with deadline_processed field
        """
        processed_todos = []
        base_time = None

        # Parse base time from received_at
        if received_at:
            try:
                base_time = date_parser.parse(received_at)
            except (ValueError, TypeError) as e:
                logger.warning(
                    f"Failed to parse received_at '{received_at}': {e}. "
                    f"Using current time as fallback."
                )

        if not base_time:
            base_time = timezone.now()

        for todo in todos:
            if not isinstance(todo, dict):
                logger.warning(f"Invalid TODO item (not a dict): {todo}")
                continue

            content = todo.get('content', '').strip()
            if not content:
                logger.warning("Skipping TODO item with empty content")
                continue

            # Process deadline
            deadline_str = (
                todo.get('deadline', '').strip()
                if todo.get('deadline') else None
            )
            deadline_processed = None

            if deadline_str:
                try:
                    deadline_processed = date_parser.parse(deadline_str)
                    logger.debug(
                        f"Parsed deadline '{deadline_str}' "
                        f"to {deadline_processed}"
                    )
                except (ValueError, TypeError) as e:
                    logger.warning(
                        f"Failed to parse deadline '{deadline_str}': {e}. "
                        f"Using base time as fallback."
                    )
                    deadline_processed = base_time
            else:
                # No time clue, use base time
                deadline_processed = base_time
                logger.debug(
                    f"No deadline provided for TODO "
                    f"'{content[:50]}...', "
                    f"using base time: {deadline_processed}"
                )

            # Validate priority
            priority = (
                todo.get('priority', '').strip().lower()
                if todo.get('priority') else None
            )
            if priority and priority not in ['high', 'medium', 'low']:
                logger.warning(
                    f"Invalid priority '{priority}' for TODO "
                    f"'{content[:50]}...'. Setting to None."
                )
                priority = None

            # Clean up other fields
            owner = (
                todo.get('owner', '').strip()
                if todo.get('owner') else None
            )
            location = (
                todo.get('location', '').strip()
                if todo.get('location') else None
            )

            processed_todo = {
                'content': content,
                'owner': owner,
                'location': location,
                'priority': priority,
                'deadline_processed': (
                    deadline_processed.isoformat()
                    if deadline_processed else None
                ),
                'deadline_original': deadline_str,
            }
            processed_todos.append(processed_todo)

        return processed_todos

    def _build_prompt_context(self, state: EmailState) -> str:
        """
        Build LLM prompt context with current time and timezone info.

        Args:
            state: Current email state

        Returns:
            str: Formatted context string
        """
        subject = state.get('subject', '') or ''
        llm_content = state.get('llm_content', '') or ''
        user_timezone = state.get('user_timezone') or 'UTC'

        current_utc = timezone.now()
        current_utc_str = current_utc.isoformat()

        local_time_str = current_utc_str
        if user_timezone:
            try:
                local_time = current_utc.astimezone(ZoneInfo(user_timezone))
                local_time_str = local_time.isoformat()
            except Exception as exc:
                logger.warning(
                    "Failed to convert timezone '%s': %s",
                    user_timezone,
                    exc
                )

        context_parts = [
            f"Subject: {subject}",
            f"Processing Timestamp (UTC): {current_utc_str}",
            f"User Timezone: {user_timezone}",
            (
                f"Processing Timestamp ({user_timezone}): "
                f"{local_time_str}"
            ),
            (
                "Important: Dates and times discussed in the following "
                "content should be interpreted using the provided user "
                "timezone unless explicitly stated otherwise."
            ),
            f"Text Content: {llm_content}",
        ]

        return "\n".join(context_parts) + "\n"

    def _build_summary_content(
        self,
        summary_data: Dict[str, Any] | None,
        processed_todos: List[Dict[str, Any]] | None,
        existing_summary_content: str = ''
    ) -> str:
        """
        Build summary_content from structured data for metadata_node.

        This method generates a text representation of the summary data
        including details, TODOs, and key processes. This is required by
        metadata_node to extract metadata from the summary.

        Args:
            summary_data: Dictionary containing 'details' and 'key_process'
            processed_todos: List of processed TODO items
            existing_summary_content: Existing summary content as fallback

        Returns:
            Formatted summary content string
        """
        content_parts = []

        # Add details section
        if summary_data and summary_data.get('details'):
            content_parts.append(summary_data['details'])

        # Add TODO section
        if processed_todos:
            content_parts.append("\nTODO:")
            for todo in processed_todos:
                if not isinstance(todo, dict):
                    continue
                todo_content = todo.get('content', '')
                if not todo_content:
                    continue
                todo_parts = [todo_content]
                if todo.get('owner'):
                    owner = todo['owner']
                    todo_parts.append(f"Owner: {owner}")
                if todo.get('deadline_original'):
                    deadline = todo['deadline_original']
                    todo_parts.append(f"Deadline: {deadline}")
                if todo.get('location'):
                    location = todo['location']
                    todo_parts.append(f"Location: {location}")
                if todo.get('priority'):
                    priority = todo['priority']
                    todo_parts.append(f"Priority: {priority}")
                todo_line = f"- {' | '.join(todo_parts)}"
                content_parts.append(todo_line)

        # Add key processes section
        if summary_data and summary_data.get('key_process'):
            key_process_list = summary_data['key_process']
            if (
                isinstance(key_process_list, list)
                and key_process_list
            ):
                content_parts.append("\nKey Processes:")
                for i, process in enumerate(key_process_list, 1):
                    content_parts.append(f"{i}. {process}")

        # Return generated content or fallback to existing
        return (
            "\n".join(content_parts)
            if content_parts
            else existing_summary_content or ''
        )

    def execute_processing(self, state: EmailState) -> EmailState:
        """
        Execute summary generation.

        Generates structured JSON (details, key_process, todo) and processes
        TODO items with time handling. summary_content is only generated in
        fallback mode when JSON generation fails.

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

        content = self._build_prompt_context(state)

        logger.info(
            "Using LLM-processed content and timezone context "
            "for summary generation"
        )

        summary_data = state.get('summary_data')
        summary_content = state.get('summary_content', '')
        summary_title = state.get('summary_title', '')
        existing_todos = state.get('todos') or []

        try:
            # Generate summary_title (still using Markdown mode)
            if not summary_title or force:
                logger.info("Generating summary title")
                summary_title_raw, usage = LLMTracker.call_and_track(
                    prompt=summary_title_prompt,
                    content=content,
                    json_mode=False,
                    state=state,
                    node_name=self.node_name
                )
                if summary_title_raw:
                    summary_title = summary_title_raw.strip()
                else:
                    summary_title = ''

            # Generate structured summary (JSON mode)
            if not summary_data or force:
                logger.info("Generating structured summary (JSON mode)")
                try:
                    # LLMTracker.call_and_track with json_mode=True
                    # automatically parses JSON and returns dict
                    summary_json, usage = LLMTracker.call_and_track(
                        prompt=summary_prompt,
                        content=content,
                        json_mode=True,
                        state=state,
                        node_name=self.node_name
                    )

                    # Extract structured data
                    summary_data = {
                        'details': summary_json.get('details', '').strip(),
                        'key_process': summary_json.get('key_process', [])
                    }

                    # Process TODOs
                    raw_todos = summary_json.get('todos', [])
                    if raw_todos:
                        received_at = state.get('received_at', '')
                        processed_todos = self._process_todos(
                            raw_todos,
                            received_at
                        )
                        logger.info(
                            f"Processed {len(processed_todos)} TODO items"
                        )
                    else:
                        processed_todos = []
                        logger.info("No TODO items found in summary")

                    # Generate summary_content from structured data for
                    # metadata_node
                    summary_content = self._build_summary_content(
                        summary_data=summary_data,
                        processed_todos=processed_todos,
                        existing_summary_content=summary_content
                    )

                    logger.info("Structured summary generated successfully")

                except Exception as json_error:
                    logger.error(
                        f"JSON summary generation failed: {json_error}. "
                        f"Falling back to Markdown mode."
                    )
                    # Fallback to old Markdown mode
                    summary_content_raw, usage = LLMTracker.call_and_track(
                        prompt=summary_prompt,
                        content=content,
                        json_mode=False,
                        state=state,
                        node_name=self.node_name
                    )
                    if summary_content_raw:
                        summary_content = summary_content_raw.strip()
                    else:
                        summary_content = ''
                    # Keep existing summary_data if available
                    if not summary_data:
                        summary_data = {}
                    processed_todos = []

            else:
                # Use existing data, but ensure todos are processed
                processed_todos = existing_todos if existing_todos else []
                # Regenerate summary_content if needed for metadata_node
                if not summary_content and summary_data:
                    summary_content = self._build_summary_content(
                        summary_data=summary_data,
                        processed_todos=processed_todos,
                        existing_summary_content=summary_content
                    )

            return {
                **state,
                'summary_data': summary_data,
                'todos': processed_todos if processed_todos else None,
                'summary_content': summary_content,
                'summary_title': summary_title
            }

        except Exception as e:
            logger.error(f"Summary generation failed: {e}", exc_info=True)
            error_message = f'Summary generation failed: {str(e)}'
            updated_state = add_node_error(
                state,
                self.node_name,
                error_message
            )
            # Preserve existing data on error
            updated_state['summary_content'] = summary_content or ''
            updated_state['summary_title'] = summary_title or ''
            updated_state['summary_data'] = summary_data or {}
            updated_state['todos'] = existing_todos if existing_todos else None
            return updated_state
