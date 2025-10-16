"""
Issue creation node for email processing.

This node handles external issue system (JIRA) integration.
No database operations - all data comes from State.
"""

import logging
from typing import Dict, Any

from threadline.agents.nodes.base_node import BaseLangGraphNode
from threadline.agents.email_state import EmailState, add_node_error
from threadline.utils.issues.jira_handler import JiraIssueHandler

logger = logging.getLogger(__name__)


class IssueNode(BaseLangGraphNode):
    """
    Issue creation node.

    This node handles external issue system (JIRA) integration.
    No database operations - all data comes from State.

    Responsibilities:
    - Check for required summary content in State
    - Validate issue configuration from State
    - Check if issue already exists in State
    - Call external issue handler (JIRA API)
    - Upload attachments to external system
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
      - engine: Engine type ('jira', 'github', etc.)
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
        summary_content = state.get('summary_content', '').strip()
        summary_title = state.get('summary_title', '').strip()

        if not force and (not summary_content or not summary_title):
            logger.error(
                "Missing summary content or title for issue creation"
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
        issue_engine = issue_config.get('issue_engine', 'jira')

        if issue_engine != 'jira':
            error_message = f'Unsupported issue engine: {issue_engine}'
            logger.error(error_message)
            return add_node_error(state, self.node_name, error_message)

        jira_result = self._create_jira_issue(state, issue_config)

        if not jira_result:
            error_message = 'JIRA issue creation failed'
            logger.error(error_message)
            return add_node_error(state, self.node_name, error_message)

        issue_key = jira_result.get('issue_key')
        logger.info(
            f"JIRA issue created successfully: {issue_key}"
        )

        # Prepare engine-agnostic issue result data
        issue_result = {
            'external_id': jira_result.get('issue_key'),
            'issue_url': jira_result.get('issue_url'),
            'title': jira_result.get('title'),
            'description': jira_result.get('description'),
            'priority': jira_result.get('priority'),
            'engine': 'jira',
            'metadata': {
                'project': jira_result.get('project'),
                'upload_result': jira_result.get('upload_result')
            }
        }

        # Add to state
        updated_state = {
            **state,
            'issue_result_data': issue_result
        }

        # Log for debugging
        logger.info(
            f"Returning state with issue_result_data: "
            f"engine=jira, external_id={issue_result.get('external_id')}, "
            f"issue_url={issue_result.get('issue_url')}"
        )

        return updated_state

    def _create_jira_issue(
        self,
        state: EmailState,
        issue_config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        """
        Create JIRA issue via API (no database operations).

        This method only calls JIRA API using data from State.
        Database record creation is handled by WorkflowFinalizeNode.

        TODO: JiraIssueHandler currently requires Issue and EmailMessage
        objects. This needs to be refactored to accept pure data dictionaries
        instead. For now, we call methods that expect these objects to exist
        in State or be constructed from State data.

        The ideal interface should be:
        - jira_handler.create_issue_from_data(issue_data, attachments, force)
        - jira_handler.upload_attachments_from_data(issue_key, attachments)

        Args:
            state: Current email state containing all necessary data
            issue_config: Issue configuration from State

        Returns:
            Dict with JIRA result data:
            - issue_key: JIRA issue key
            - issue_url: Full URL to JIRA issue
            - project: JIRA project key
            - title: Issue title
            - description: Issue description
            - priority: Issue priority
            - upload_result: Attachment upload result
            None if creation failed
        """
        try:
            jira_config = issue_config.get('jira')

            if not jira_config:
                logger.warning(
                    "JIRA config not found, skipping JIRA creation"
                )
                return None

            title = state.get('summary_title', 'Email Issue')
            description = state.get('summary_content', 'No content')
            priority = jira_config.get('default_priority', 'Medium')
            email_id = state.get('id')
            user_id = state.get('user_id')
            attachments = state.get('attachments', [])

            jira_handler = JiraIssueHandler(jira_config)
            force = state.get('force', False)

            logger.info(
                f"Creating JIRA issue with title: {title[:50]}..."
            )

            issue_data = {
                'title': title,
                'description': description,
                'priority': priority,
            }

            email_data = {
                'id': email_id,
                'summary_title': title,
                'summary_content': description,
                'llm_content': state.get('llm_content', ''),
                'subject': state.get('subject', ''),
            }

            issue_key = jira_handler.create_issue(
                issue_data=issue_data,
                email_data=email_data,
                attachments=attachments,
                force=force
            )
            email_id = state.get('id')
            user_id = state.get('user_id')
            logger.info(
                f"[{self.node_name}] Created JIRA issue {issue_key} for "
                f"email {email_id}, user {user_id}"
            )

            upload_result = jira_handler.upload_attachments(
                issue_key=issue_key,
                attachments=attachments
            )
            logger.info(
                f"Uploaded {upload_result['uploaded_count']} attachments "
                f"to JIRA {issue_key} for email {email_id}"
            )

            issue_url = f"{jira_config['url']}/browse/{issue_key}"
            project_key = (
                issue_key.split('-')[0]
                if '-' in issue_key else None
            )

            return {
                'issue_key': issue_key,
                'issue_url': issue_url,
                'project': project_key,
                'title': title,
                'description': description,
                'priority': priority,
                'engine': 'jira',
                'upload_result': upload_result
            }

        except AttributeError as e:
            logger.error(
                f"JiraIssueHandler interface issue: {e}. "
                f"Handler needs to be refactored to accept pure data."
            )
            return None
        except Exception as e:
            logger.error(f"JIRA issue creation failed: {e}")
            return None
