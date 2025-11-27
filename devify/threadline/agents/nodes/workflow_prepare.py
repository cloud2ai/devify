"""
Workflow prepare node for email processing.

This node handles all initial validation, database setup, and state
preparation when starting the email processing workflow. It serves as
the single entry point for all database validations and initializations.
"""

import logging

from django.conf import settings as django_settings
from django.core.exceptions import ObjectDoesNotExist

from billing.services.subscription_service import SubscriptionService
from threadline.agents.nodes.base_node import BaseLangGraphNode
from threadline.agents.email_state import EmailState
from threadline.models import EmailMessage, Issue, Settings, EmailTodo
from threadline.state_machine import EmailStatus
from threadline.utils.prompt_config_manager import PromptConfigManager

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
    - Set database status to PROCESSING (always, regardless of force mode)
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

    def _load_prompt_config(self, state: EmailState) -> dict | None:
        """
        Load prompt configuration for the user.

        Supports retry configuration override via retry_language
        and retry_scene in state.

        Args:
            state: Current email state

        Returns:
            dict: Prompt configuration or None if failed
        """
        retry_language = state.get('retry_language')
        retry_scene = state.get('retry_scene')

        try:
            prompt_manager = PromptConfigManager()

            if retry_language or retry_scene:
                if retry_language and retry_scene:
                    scene = retry_scene
                    language = retry_language
                else:
                    try:
                        user_config = Settings.get_user_prompt_config(
                            self.email.user
                        )
                    except ValueError:
                        user_config = {}

                    if retry_scene:
                        scene = retry_scene
                    else:
                        scene = user_config.get(
                            'scene', django_settings.DEFAULT_SCENE
                        )

                    if retry_language:
                        language = retry_language
                    else:
                        language = user_config.get(
                            'language', django_settings.DEFAULT_LANGUAGE
                        )

                logger.info(
                    f"Using retry configuration for email "
                    f"{self.email.id}, user {self.email.user_id}: "
                    f"language={language}, scene={scene} "
                    f"(retry_language={retry_language}, "
                    f"retry_scene={retry_scene})"
                )
                prompt_config = prompt_manager.get_prompt_config(
                    scene, language
                )
            else:
                prompt_config = prompt_manager.load_prompt_config(
                    self.email.user
                )

            logger.info(
                f"Loaded prompt_config for user {self.email.user_id}"
            )
            return prompt_config
        except Exception as e:
            logger.error(
                f"Failed to load prompt_config for user "
                f"{self.email.user_id}: {e}"
            )
            return None

    def _load_issue_config(self) -> dict | None:
        """
        Load issue configuration for the user.

        Returns:
            dict: Issue configuration or None if failed
        """
        try:
            issue_config = Settings.get_user_config(
                self.email.user, 'issue_config'
            )
            logger.info(
                f"Loaded issue_config for user {self.email.user_id}"
            )
            return issue_config
        except ValueError as e:
            logger.warning(
                f"Failed to load issue_config for user "
                f"{self.email.user_id}: {e}"
            )
            return None

    def _get_max_attachments(self) -> int | None:
        """
        Get user's attachment count limit from subscription plan.

        Returns:
            int: Maximum attachment count or None
        """
        if not django_settings.BILLING_ENABLED:
            return None

        try:
            subscription = SubscriptionService.get_active_subscription(
                self.email.user_id
            )
            if subscription and subscription.plan:
                max_attachments = subscription.plan.metadata.get(
                    'max_attachment_count'
                )
                logger.info(
                    f"User {self.email.user_id} subscription plan: "
                    f"{subscription.plan.slug}, "
                    f"max attachments count: {max_attachments}"
                )
                return max_attachments
        except Exception as e:
            logger.warning(
                f"Failed to get subscription for user "
                f"{self.email.user_id}: {e}"
            )
        return None

    def _load_attachments_data(self) -> list:
        """
        Load attachment data from EmailMessage.

        Returns:
            list: List of attachment data dictionaries
        """
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
        return attachments_data

    def _load_existing_issue_metadata(
        self
    ) -> tuple[int | None, str | None, dict | None]:
        """
        Load existing issue information for the email.

        Returns:
            tuple: (issue_id, issue_url, issue_metadata)
        """
        existing_issue = Issue.objects.filter(
            email_message=self.email
        ).first()

        if not existing_issue:
            return None, None, None

        issue_metadata = {
            'engine': existing_issue.engine,
            'external_id': existing_issue.external_id,
            'title': existing_issue.title,
            'priority': existing_issue.priority,
        }

        if existing_issue.engine == 'jira':
            issue_metadata['key'] = existing_issue.external_id
            if (
                existing_issue.external_id and
                '-' in existing_issue.external_id
            ):
                issue_metadata['project'] = (
                    existing_issue.external_id.split('-')[0]
                )
            else:
                issue_metadata['project'] = None

        return (
            existing_issue.id,
            existing_issue.issue_url,
            issue_metadata
        )

    def _load_todos_data(self) -> list:
        """
        Load existing TODOs for this email.

        Returns:
            list: List of TODO data dictionaries
        """
        existing_todos = EmailTodo.objects.filter(
            email_message=self.email
        ).order_by('created_at')

        todos_data = []
        for todo in existing_todos:
            todos_data.append({
                'id': todo.id,
                'content': todo.content,
                'is_completed': todo.is_completed,
                'completed_at': (
                    todo.completed_at.isoformat()
                    if todo.completed_at else None
                ),
                'priority': todo.priority,
                'owner': todo.owner,
                'deadline': (
                    todo.deadline.isoformat()
                    if todo.deadline else None
                ),
                'location': todo.location,
                'metadata': todo.metadata or {},
            })
        return todos_data

    def _build_email_state(
        self,
        state: EmailState,
        prompt_config: dict | None,
        issue_config: dict | None,
        max_attachments: int | None,
        attachments_data: list,
        issue_id: int | None,
        issue_url: str | None,
        issue_metadata: dict | None,
        summary_data: dict | None,
        todos_data: list
    ) -> EmailState:
        """
        Build the final EmailState dictionary with all loaded data.

        Args:
            state: Current email state
            prompt_config: Loaded prompt configuration
            issue_config: Loaded issue configuration
            max_attachments: Maximum attachment count
            attachments_data: List of attachment data
            issue_id: Existing issue ID
            issue_url: Existing issue URL
            issue_metadata: Existing issue metadata
            summary_data: Summary data from EmailMessage
            todos_data: List of TODO data

        Returns:
            EmailState: Complete state dictionary
        """
        return {
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
            'html_content': self.email.html_content,
            'text_content': self.email.text_content,
            'attachments': attachments_data,
            'max_attachments': max_attachments,
            'summary_title': self.email.summary_title or None,
            'summary_content': self.email.summary_content or None,
            'summary_data': summary_data,
            'todos': todos_data if todos_data else None,
            'llm_content': self.email.llm_content or None,
            'metadata': self.email.metadata or None,
            'issue_id': issue_id,
            'issue_url': issue_url,
            'issue_metadata': issue_metadata,
            'prompt_config': prompt_config,
            'issue_config': issue_config,
            'user_timezone': self._get_user_timezone(),
            'created_at': (
                self.email.created_at.isoformat()
                if self.email.created_at else None
            ),
            'updated_at': (
                self.email.updated_at.isoformat()
                if self.email.updated_at else None
            )
        }

    def _get_user_timezone(self) -> str:
        """
        Get user's timezone preference for prompt context.

        Returns:
            str: Timezone string (e.g., 'Asia/Shanghai') or 'UTC'
        """
        default_timezone = getattr(
            django_settings,
            'DEFAULT_USER_TIMEZONE',
            'UTC'
        )

        user = self.email.user

        # Attempt to fetch timezone from user profile
        try:
            profile = getattr(user, 'profile', None)
            if profile and getattr(profile, 'timezone', None):
                return profile.timezone
        except ObjectDoesNotExist:
            pass
        except Exception as exc:
            logger.warning(
                "Failed to load timezone from profile for user %s: %s",
                user.id,
                exc
            )

        # Fallback to subscription settings if available
        try:
            settings_timezone = Settings.get_user_config(
                user,
                'timezone'
            )
            if isinstance(settings_timezone, str) and settings_timezone:
                return settings_timezone
        except ValueError:
            pass
        except Exception as exc:
            logger.warning(
                "Failed to load timezone from Settings for user %s: %s",
                user.id,
                exc
            )

        return default_timezone

    def execute_processing(self, state: EmailState) -> EmailState:
        """
        Execute the workflow preparation logic.

        Populate the EmailState with all data from the database
        EmailMessage and user Settings. Always set database status
        to PROCESSING (force mode does not affect status updates).

        Args:
            state: Current email state

        Returns:
            EmailState: Updated state with all email data and configurations
        """
        self.email.set_status(EmailStatus.PROCESSING.value)
        force = state.get('force', False)
        logger.info(
            f"[{self.node_name}] Status set to PROCESSING for "
            f"email {self.email.id}, user {self.email.user_id}, "
            f"force={force}"
        )

        prompt_config = self._load_prompt_config(state)
        issue_config = self._load_issue_config()
        max_attachments = self._get_max_attachments()
        attachments_data = self._load_attachments_data()
        issue_id, issue_url, issue_metadata = (
            self._load_existing_issue_metadata()
        )
        summary_data = self.email.summary_data or None
        todos_data = self._load_todos_data()

        updated_state = self._build_email_state(
            state,
            prompt_config,
            issue_config,
            max_attachments,
            attachments_data,
            issue_id,
            issue_url,
            issue_metadata,
            summary_data,
            todos_data
        )

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
