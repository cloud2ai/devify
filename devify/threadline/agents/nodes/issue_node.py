"""
Issue creation node for email processing.

This node handles external issue system (JIRA) integration.
No database operations - all data comes from State.
"""

import logging
from typing import Dict, Any

from threadline.agents.nodes.base_node import BaseLangGraphNode
from threadline.agents.email_state import EmailState, add_node_error
from threadline.utils.issues import get_issue_handler
from threadline.utils.issues.issue_factory import normalize_issue_engine
from threadline.utils.issues.jira_utils import build_description_field

logger = logging.getLogger(__name__)


class IssueNode(BaseLangGraphNode):
    """
    Issue creation node.

    This node handles external issue system integration.
    No database operations - all data comes from State.

    Responsibilities:
    - Check for required summary content in State
    - Validate issue configuration from State
    - Check if issue already exists in State
    - Call the configured external issue handler
    - Upload attachments when the provider supports it
    - Store JIRA result in State for WorkflowFinalizeNode
    - Skip if issue already exists (unless force mode)

    State Input Requirements:
    - summary_title: Issue title
    - summary_content: Issue description
    - issue_config: Issue configuration dict
    - user_id: User ID
    - attachments: List of attachment data

    State Output:
    - issue_result_data: Dict containing engine-agnostic issue data
      - external_id: Issue ID in external system
      - issue_url: Full URL to issue in external system
      - title: Issue title
      - description: Issue description
      - priority: Issue priority
      - engine: Engine type ('jira', 'feishu_bitable', etc.)
      - metadata: Engine-specific data (varies by engine)
    """

    def __init__(self):
        super().__init__("issue_node")

    def can_enter_node(self, state: EmailState) -> bool:
        """
        Check if Issue node can enter.

        Issue node can enter ONLY if ALL of the following are true:
        - No errors in previous nodes (force mode does NOT bypass this)
        - Has summary content for issue creation
        - Issue creation is enabled in configuration (from State)

        Args:
            state (EmailState): Current email state

        Returns:
            bool: True if node can enter, False otherwise
        """
        # Critical: If any previous node failed, do NOT create issue
        # This applies even in force mode - we never create issues
        # when there are errors in the workflow
        if not super().can_enter_node(state):
            logger.info(
                "Skipping issue creation due to errors in previous nodes"
            )
            return False

        force = state.get('force', False)
        summary_title = state.get('summary_title', '').strip()
        # Check for summary data - prefer structured data,
        # fallback to summary_content
        summary_data = state.get('summary_data')
        todos = state.get('todos')
        summary_content = state.get('summary_content', '').strip()

        # Need either summary_title and (summary_data/todos OR
        # summary_content)
        has_summary_data = (
            (summary_data and summary_data.get('details')) or todos
        )
        has_summary_content = summary_content and summary_content.strip()

        if not force and (
            not summary_title
            or (not has_summary_data and not has_summary_content)
        ):
            logger.error(
                "Missing summary title or content for issue creation. "
                "Need either summary_data/todos or summary_content."
            )
            return False

        issue_config = state.get('issue_config')
        if not issue_config or not issue_config.get('enable', False):
            email_id = state.get('id')
            user_id = state.get('user_id')
            logger.info(
                f"Issue creation disabled for email {email_id}, "
                f"user {user_id}, skipping"
            )
            return False

        # Check if issue was already created in current workflow run
        # This prevents creating duplicate issues within the same execution
        existing_issue_data = state.get('issue_result_data')
        if not force and existing_issue_data:
            logger.info(
                f"Issue already created in current workflow run "
                f"(external_id: {existing_issue_data.get('external_id')}), "
                f"skipping"
            )
            return False

        # Note: We do NOT check database for existing Issue records
        # The Issue model supports one-to-many relationship
        # (one email can have multiple issues)
        # This allows users to:
        # - Create multiple issues for the same email if needed
        # - Use force=true to recreate issues with different configs
        # - Have full control over issue lifecycle
        # Users should manage duplicate issues themselves if needed

        return True

    def execute_processing(self, state: EmailState) -> EmailState:
        """
        Execute issue creation in external system.

        Calls configured issue engine API to create issue and
        upload attachments. Does NOT create database records
        (handled by WorkflowFinalizeNode). All data comes from State.

        Args:
            state (EmailState): Current email state

        Returns:
            EmailState: Updated state with issue_result_data
        """
        issue_config = state.get('issue_config', {})
        issue_engine = normalize_issue_engine(
            issue_config.get('issue_engine', 'jira')
        )

        try:
            issue_handler = get_issue_handler(issue_config)
        except ValueError as e:
            error_message = str(e)
            logger.error(error_message)
            return add_node_error(state, self.node_name, error_message)

        provider_result = self._create_issue(
            state, issue_config, issue_handler
        )

        if not provider_result:
            error_message = f"{issue_engine} issue creation failed"
            logger.error(error_message)
            return add_node_error(state, self.node_name, error_message)

        issue_key = provider_result.get('issue_key')
        logger.info(
            f"{issue_engine} issue created successfully: {issue_key}"
        )

        # Prepare engine-agnostic issue result data
        issue_result_data = {
            'external_id': provider_result.get('issue_key'),
            'issue_url': provider_result.get('issue_url'),
            'title': provider_result.get('title'),
            'description': provider_result.get('description'),
            'priority': provider_result.get('priority'),
            'engine': issue_engine,
            'metadata': provider_result.get('metadata', {})
        }

        # Add to state
        updated_state = {
            **state,
            'issue_result_data': issue_result_data
        }

        # Log for debugging
        logger.info(
            f"Returning state with issue_result_data: "
            f"engine={issue_engine}, external_id={issue_result_data.get('external_id')}, "
            f"issue_url={issue_result_data.get('issue_url')}"
        )

        return updated_state

    def _normalize_language(self, language: str) -> str:
        """
        Normalize language code for JIRA formatting.

        Args:
            language: Language code (e.g., 'zh-CN', 'en-US')

        Returns:
            Normalized language code (e.g., 'zh', 'en')
        """
        if language.startswith('zh'):
            return 'zh'
        elif language.startswith('en'):
            return 'en'
        return language

    def _extract_language_from_state(
        self, state: EmailState
    ) -> str:
        """
        Extract and normalize language from prompt_config.

        Args:
            state: Current email state

        Returns:
            Normalized language code
        """
        prompt_config = state.get('prompt_config', {})
        language = (
            prompt_config.get('language', 'en')
            if isinstance(prompt_config, dict) else 'en'
        )
        return self._normalize_language(language)

    def _prepare_issue_data(
        self,
        state: EmailState,
        jira_config: Dict[str, Any]
    ) -> tuple[Dict[str, Any], Dict[str, Any], str]:
        """
        Prepare issue_data and email_data for JIRA creation.

        Args:
            state: Current email state
            jira_config: JIRA configuration

        Returns:
            Tuple of (issue_data, email_data, language)
        """
        title = state.get('summary_title', 'Email Issue')
        summary_content = state.get('summary_content', 'No content')
        summary_data = state.get('summary_data')
        todos = state.get('todos')
        priority = jira_config.get('default_priority', 'Medium')
        language = self._extract_language_from_state(state)

        issue_data = {
            'title': title,
            'description': summary_content,  # Will be replaced by handler
            'priority': priority,
        }

        email_data = {
            'id': state.get('id'),
            'summary_title': title,
            'summary_content': summary_content,
            'summary_data': summary_data,
            'todos': todos,
            'llm_content': state.get('llm_content', ''),
            'subject': state.get('subject', ''),
            'metadata': state.get('metadata', {}),
            'language': language,
        }

        return issue_data, email_data, language

    def _build_issue_description(
        self,
        state: EmailState,
        jira_config: Dict[str, Any],
        language: str
    ) -> str:
        """
        Build description for issue result data.

        JIRA handler already processed and sent description to JIRA.
        We build it here for the result data structure.

        Args:
            state: Current email state
            jira_config: JIRA configuration
            language: Language code for formatting

        Returns:
            Formatted description string
        """
        summary_content = state.get('summary_content', 'No content')
        summary_data = state.get('summary_data')
        todos = state.get('todos')
        llm_content = state.get('llm_content', '')
        attachments = state.get('attachments', [])
        convert_to_jira_wiki = jira_config.get(
            'convert_to_jira_wiki', False
        )

        return build_description_field(
            summary_content=summary_content,
            llm_content=llm_content,
            attachments=attachments,
            convert_to_jira_wiki=convert_to_jira_wiki,
            summary_data=summary_data,
            todos=todos,
            language=language
        )

    def _create_issue(
        self,
        state: EmailState,
        issue_config: Dict[str, Any],
        issue_handler: Any
    ) -> Dict[str, Any] | None:
        """
        Create an external issue record via the configured provider.

        This method only calls the provider API using data from State.
        Database record creation is handled by WorkflowFinalizeNode.

        Args:
            state: Current email state containing all necessary data
            issue_config: Issue configuration from State
            issue_handler: Provider-specific issue handler

        Returns:
            Dict with provider result data:
            - issue_key: External record identifier
            - issue_url: Full URL to external record
            - title: Issue title
            - description: Issue description
            - priority: Issue priority
            - upload_result: Attachment upload result
            None if creation failed
        """
        try:
            provider_key = normalize_issue_engine(
                issue_config.get('issue_engine', 'jira')
            )
            provider_config = issue_config.get(provider_key, {})

            if not provider_config:
                logger.warning(
                    "Provider config not found, skipping issue creation"
                )
                return None

            # Prepare data for JIRA creation
            issue_data, email_data, language = self._prepare_issue_data(
                state, provider_config
            )

            force = state.get('force', False)
            attachments = state.get('attachments', [])
            email_id = state.get('id')
            user_id = state.get('user_id')

            title = issue_data['title']
            logger.info(
                f"Creating issue with title: {title[:50]}..."
            )

            # Create external issue record
            issue_key = issue_handler.create_issue(
                issue_data=issue_data,
                email_data=email_data,
                attachments=attachments,
                force=force
            )
            logger.info(
                f"[{self.node_name}] Created external record {issue_key} for "
                f"email {email_id}, user {user_id}"
            )

            upload_result = None
            if provider_key != 'feishu_bitable':
                # Upload attachments when the provider supports it
                upload_result = issue_handler.upload_attachments(
                    issue_key=issue_key,
                    attachments=attachments
                )
                logger.info(
                    f"Uploaded {upload_result['uploaded_count']} "
                    f"attachments for external record {issue_key} and "
                    f"email {email_id}"
                )

            # Build result data
            issue_url = issue_handler.get_issue_url(issue_key)
            project_key = provider_config.get('project_key')

            description = self._build_issue_description(
                state, provider_config, language
            )

            return {
                'issue_key': issue_key,
                'issue_url': issue_url,
                'project': project_key,
                'title': title,
                'description': description,
                'priority': issue_data['priority'],
                'engine': provider_key,
                'upload_result': upload_result,
                'metadata': {
                    'provider': provider_key,
                    **(
                        {'upload_result': upload_result}
                        if upload_result is not None else {}
                    ),
                }
            }

        except Exception as e:
            logger.error(f"Issue creation failed: {e}")
            return None
