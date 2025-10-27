"""
Workflow prepare node for email processing.

This node handles all initial validation, database setup, and state
preparation when starting the email processing workflow. It serves as
the single entry point for all database validations and initializations.
"""

import logging
from typing import Dict, Any

from threadline.agents.nodes.base_node import BaseLangGraphNode
from threadline.agents.email_state import EmailState, add_node_error
from threadline.models import EmailMessage, Issue, Settings
from threadline.state_machine import EmailStatus

logger = logging.getLogger(__name__)


class WorkflowPrepareNode(BaseLangGraphNode):
    """
    Workflow prepare node for email processing workflow.

    This node serves as the single entry point for all database
    validations, initializations, and state preparation. It ensures
    all necessary data is loaded into the EmailState, eliminating the
    need for subsequent nodes to perform database queries.

    Responsibilities:
    - Validate email_id and load EmailMessage object
    - Load all attachments information
    - Load user Settings configurations (prompt_config, issue_config)
    - Initialize EmailState with all necessary data
    - Set database status to PROCESSING (skip in force mode)
    - Provide comprehensive validation for the entire workflow
    """

    def __init__(self):
        super().__init__("workflow_prepare_node")
        self.email = None

    def can_enter_node(self, state: EmailState) -> bool:
        """
        Check if workflow prepare node can enter.

        Workflow prepare is the entry point, so we use simpler logic:
        - Force mode: always allow entry
        - Normal mode: check for existing errors

        Args:
            state: Current email state

        Returns:
            bool: True if node can enter, False otherwise
        """
        force = state.get('force', False)
        if force:
            email_id = state.get('id')
            user_id = state.get('user_id')
            logger.info(
                f"Force mode enabled for email {email_id}, user {user_id}"
            )
            return True

        return super().can_enter_node(state)

    def before_processing(self, state: EmailState) -> EmailState:
        """
        Pre-processing: Basic validation and load EmailMessage.

        Args:
            state: Current email state

        Returns:
            EmailState: Updated state after basic validation
        """
        email_id = state.get('id')
        if not email_id:
            raise ValueError('email_id is required in state')

        try:
            self.email = EmailMessage.objects.select_related(
                'user'
            ).prefetch_related('attachments').get(id=email_id)
        except EmailMessage.DoesNotExist:
            raise ValueError(f'EmailMessage {email_id} not found')

        logger.info(
            f"[{self.node_name}] EmailMessage loaded: email {email_id}, "
            f"user {self.email.user_id}"
        )
        return state

    def execute_processing(self, state: EmailState) -> EmailState:
        """
        Execute the workflow preparation logic.

        Populate the EmailState with all data from the database
        EmailMessage and user Settings. Optionally set database status
        to PROCESSING based on force parameter.

        Args:
            state: Current email state

        Returns:
            EmailState: Updated state with all email data and configurations
        """
        force = state.get('force', False)

        if not force:
            self.email.set_status(EmailStatus.PROCESSING.value)
            logger.info(
                f"[{self.node_name}] Status set to PROCESSING for "
                f"email {self.email.id}, user {self.email.user_id}"
            )
        else:
            logger.info(
                f"Force mode: skipping status update for "
                f"email {self.email.id}, status remains {self.email.status}"
            )

        prompt_config = None
        issue_config = None
        try:
            prompt_config = Settings.get_user_prompt_config(self.email.user)
            logger.info(
                f"Loaded prompt_config for user {self.email.user_id}"
            )
        except ValueError as e:
            logger.warning(
                f"Failed to load prompt_config for user "
                f"{self.email.user_id}: {e}"
            )

        try:
            issue_config = Settings.get_user_config(
                self.email.user, 'issue_config'
            )
            logger.info(
                f"Loaded issue_config for user {self.email.user_id}"
            )
        except ValueError as e:
            logger.warning(
                f"Failed to load issue_config for user "
                f"{self.email.user_id}: {e}"
            )

        attachments_data = []
        for att in self.email.attachments.all():
            attachments_data.append({
                'id': str(att.id),
                'filename': att.filename,
                'safe_filename': att.safe_filename,
                'content_type': att.content_type,
                'file_size': att.file_size,
                'file_path': att.file_path,
                'is_image': att.is_image,
                'ocr_content': att.ocr_content or None,
                'llm_content': att.llm_content or None,
            })

        existing_issue = Issue.objects.filter(
            email_message=self.email
        ).first()

        issue_metadata = None
        if existing_issue:
            issue_metadata = {
                'engine': existing_issue.engine,
                'external_id': existing_issue.external_id,
                'title': existing_issue.title,
                'priority': existing_issue.priority,
            }
            if existing_issue.engine == 'jira':
                issue_metadata['key'] = existing_issue.external_id
                issue_metadata['project'] = (
                    existing_issue.external_id.split('-')[0]
                    if (
                        existing_issue.external_id and
                        '-' in existing_issue.external_id
                    )
                    else None
                )

        updated_state = {
            **state,
            'id': str(self.email.id),
            'user_id': str(self.email.user_id),
            'message_id': self.email.message_id,
            'subject': self.email.subject,
            'sender': self.email.sender,
            'recipients': self.email.recipients,
            'received_at': (
                self.email.received_at.isoformat()
                if self.email.received_at else ''
            ),
            'raw_content': self.email.raw_content,
            'html_content': self.email.html_content,
            'text_content': self.email.text_content,
            'attachments': attachments_data,
            'summary_title': self.email.summary_title or None,
            'summary_content': self.email.summary_content or None,
            'llm_content': self.email.llm_content or None,
            'metadata': self.email.metadata or None,
            'issue_id': existing_issue.id if existing_issue else None,
            'issue_url': existing_issue.issue_url if existing_issue else None,
            'issue_metadata': issue_metadata,
            'prompt_config': prompt_config,
            'issue_config': issue_config,
            'created_at': (
                self.email.created_at.isoformat()
                if self.email.created_at else None
            ),
            'updated_at': (
                self.email.updated_at.isoformat()
                if self.email.updated_at else None
            )
        }

        logger.info(
            f"[{self.node_name}] EmailState populated for "
            f"email {self.email.id}, user {self.email.user_id}: "
            f"{len(attachments_data)} attachments, "
            f"prompt_config={'loaded' if prompt_config else 'missing'}, "
            f"issue_config={'loaded' if issue_config else 'missing'}"
        )

        return updated_state

    def after_processing(self, state: EmailState) -> EmailState:
        """
        Post-processing: Validate critical fields for subsequent nodes.

        Check essential fields that will be needed by downstream
        processing nodes. This helps catch configuration issues early
        rather than failing later.

        Args:
            state: Current email state

        Returns:
            EmailState: Validated state (with defaults for missing fields)

        Raises:
            ValueError: If critical fields are missing
        """
        # Handle missing subject with default value
        if not state.get('subject'):
            email_id = state.get('id')
            logger.warning(
                f"EmailMessage {email_id} has no subject, "
                f"using default value '(No Subject)'"
            )
            state = {**state, 'subject': '(No Subject)'}

        if not state.get('sender'):
            raise ValueError(
                f"EmailMessage {state.get('id')} missing sender - "
                f"required for processing"
            )

        if not state.get('message_id'):
            raise ValueError(
                f"EmailMessage {state.get('id')} missing message_id - "
                f"required for processing"
            )

        text_content = state.get('text_content', '')
        html_content = state.get('html_content', '')
        email_id = state.get('id')
        user_id = state.get('user_id')

        if not text_content and not html_content:
            logger.warning(
                f"Email {email_id}, user {user_id} has no text_content "
                f"or html_content - processing may have limited results"
            )

        logger.info(
            f"Email {email_id}, user {user_id} passed critical validations"
        )

        return state
