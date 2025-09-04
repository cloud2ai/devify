"""
Issue Creation Task using Celery Task class approach.

ARCHITECTURE DESIGN
==================

This module implements the final stage of the email processing pipeline,
following the same clean architecture pattern as OCR task with proper
state machine integration and centralized force logic handling.

State Machine Integration
------------------------

Allowed Input States:
  - LLM_SUMMARY_SUCCESS: Previous summary processing completed
    successfully
  - ISSUE_FAILED: Previous issue creation attempt failed, allows retry

Status Transitions:
  - LLM_SUMMARY_SUCCESS/ISSUE_FAILED → ISSUE_PROCESSING →
    ISSUE_SUCCESS (normal flow)
  - LLM_SUMMARY_SUCCESS/ISSUE_FAILED → ISSUE_PROCESSING →
    ISSUE_FAILED (error flow)
  - Special case: ISSUE_SUCCESS → COMPLETED (for JIRA integration)

Processing Logic
---------------
- Creates issues from email summaries using configured engines
- Supports multiple issue engines (JIRA, email, slack, etc.)
- Skips processing if issue already exists (unless force=True)
- Handles JIRA integration with attachment uploads
- Validates required content before processing

Force Mode Behavior
------------------
- Bypasses all status checks and validations
- Skips status updates to prevent state machine corruption
- Allows reprocessing regardless of current state
- Creates new issues even if they already exist
- Processes all content regardless of existing issues

This implementation follows the established design pattern for consistent
task architecture across the email processing pipeline.
"""

import logging
from typing import Dict, Any

from celery import Task, shared_task

from threadline.models import EmailMessage, Settings, Issue
from threadline.state_machine import EmailStatus
from threadline.tasks.issues.jira_handler import JiraIssueHandler

logger = logging.getLogger(__name__)


class IssueCreateTask(Task):
    """
    Issue creation task using Celery Task class.

    This class provides a unified execution flow for issue creation
    while keeping all logic visible and maintainable.
    """

    def before_start(self, email_id: str, force: bool = False, **kwargs):
        """
        Initialize task before execution starts.

        This method handles all initialization work including:
        - Setting instance attributes
        - Getting email object

        Args:
            email_id: ID of the email to process
            force: Whether to force processing regardless of current status
            **kwargs: Additional arguments

        Raises:
            EmailMessage.DoesNotExist: If email not found
        """
        # Set instance attributes
        self.email_id = email_id
        self.force = force
        self.email = None
        self.task_name = "ISSUE_CREATE"

        # For EmailMessage Status Control
        self.allowed_statuses = [
            EmailStatus.LLM_SUMMARY_SUCCESS.value,  # Previous step success
            EmailStatus.ISSUE_FAILED.value          # Current step failed
                                                    # (retry)
        ]
        self.next_success_status = EmailStatus.ISSUE_SUCCESS.value
        self.processing_status = EmailStatus.ISSUE_PROCESSING.value
        self.next_failed_status = EmailStatus.ISSUE_FAILED.value

        # Get email object
        try:
            self.email = EmailMessage.objects.select_related(
                'user').get(id=email_id)
            # Force refresh to get latest status from database
            self.email.refresh_from_db()
            # Cache the current status for consistent use throughout the task
            self.current_status = self.email.status
            logger.info(f"[{self.task_name}] Email object retrieved: "
                       f"{email_id}, current_status: "
                       f"{self.current_status}")
        except EmailMessage.DoesNotExist:
            logger.error(f"[{self.task_name}] EmailMessage {email_id} "
                        f"not found")
            raise

        logger.info(f"[{self.task_name}] Initialization completed for "
                   f"{email_id}, force: {force}")

    def run(self, email_id: str, force: bool = False) -> str:
        """
        Main task execution method.

        Args:
            email_id: ID of the email to process
            force: Whether to force processing regardless of current status

        Returns:
            str: The email_id for the next task in the chain
        """
        try:
            # Initialize task - always call before_start to ensure force is set
            self.before_start(email_id, force)

            logger.info(f"[{self.task_name}] Start processing: "
                        f"{email_id}, force: {force}")

            # Step 1: Pre-execution check (skip in force mode)
            if not self.force and not self._pre_execution_check():
                logger.info(f"[{self.task_name}] Pre-execution check "
                           f"failed, skipping to next task: {email_id}")
                return email_id

            # Step 2: Check if already complete (skip in force mode)
            if not self.force and self._is_already_complete():
                logger.info(f"[{self.task_name}] Email {email_id} "
                           f"already complete, skipping to next task")
                return email_id

            # Step 3: Validate required content (skip in force mode)
            if not self.force and not self._validate_required_content():
                raise ValueError("Email missing required content for "
                               "issue creation.")

            # Step 4: Set processing status (skip in force mode)
            if not self.force:
                logger.info(f"[{self.task_name}] Setting processing "
                           f"status for email {email_id}")
                self._set_processing_status()

            # Step 5: Execute core business logic
            issue_results = self._execute_issue_creation(
                force_mode=self.force)

            # Step 6: Update email status (skip in force mode)
            if not self.force:
                self._update_email_status(issue_results)
            else:
                logger.info(f"[{self.task_name}] Force mode: skipping "
                           f"status updates for {email_id}")

            logger.info(f"[{self.task_name}] Processing completed: "
                       f"{email_id}")

            return email_id

        except EmailMessage.DoesNotExist:
            logger.error(f"[{self.task_name}] EmailMessage {email_id} "
                        f"not found")
            raise
        except Exception as exc:
            logger.error(f"[{self.task_name}] Fatal error for {email_id}: "
                        f"{exc}")
            if not self.force:
                self._handle_issue_error(exc)
            else:
                logger.warning(f"[{self.task_name}] Force mode: skipping "
                              f"error handling for {email_id}")
            raise

    def _pre_execution_check(self) -> bool:
        """
        Pre-execution check: Validate if task can be executed based on
        current email status.

        Returns:
            bool: True if execution is allowed
        """
        if self.current_status not in self.allowed_statuses:
            logger.warning(f"[{self.task_name}] Email {self.email_id} "
                          f"cannot be processed in status: "
                          f"{self.current_status}. Allowed: "
                          f"{self.allowed_statuses}")
            return False

        logger.debug(f"[{self.task_name}] Pre-execution check passed for "
                    f"email {self.email_id}")
        return True

    def _is_already_complete(self) -> bool:
        """
        Check if issue creation is already complete.

        This method checks three dimensions:
        1. Issue configuration: Check if issue creation is needed
        2. EmailMessage status: Must be in correct state for issue creation
        3. Issue existence: Check if issue already exists

        Returns:
            bool: True if already complete or cannot proceed
        """
        # Check if already in success state
        if self.current_status == self.next_success_status:
            logger.info(f"[{self.task_name}] Email {self.email_id} already "
                       f"in {self.next_success_status} state, skipping to "
                       f"next task")
            return True

        # Check if issue creation is needed
        issue_config = self._get_issue_config()
        if not issue_config or not issue_config.get('enable', False):
            # Issue creation is disabled, mark as completed and skip
            logger.info(f"[{self.task_name}] Issue creation disabled for "
                       f"email {self.email_id}, marking as completed")
            self._save_email(status=EmailStatus.COMPLETED.value)
            return True

        # Check if issue already exists for this email
        existing_issue = Issue.objects.filter(
            email_message=self.email
        ).first()

        if existing_issue:
            logger.info(f"[{self.task_name}] Email {self.email_id} "
                       f"already has issue (ID: {existing_issue.id}), "
                       f"marking as completed")
            # Update status to completed since issue already exists
            self._save_email(status=EmailStatus.COMPLETED.value)
            return True

        return False

    def _validate_required_content(self) -> bool:
        """
        Validate that email has required content for issue creation.

        This method validates:
        1. Summary content exists
        2. Summary title exists
        3. Email has been properly processed

        Returns:
            bool: True if required content exists
        """
        # Check if summary content exists
        if not self.email.summary_content or not self.email.summary_content.strip():
            logger.error(
                f"Email {self.email.id} missing summary content "
                f"for issue creation"
            )
            return False

        # Check if summary title exists
        if not self.email.summary_title or not self.email.summary_title.strip():
            logger.error(
                f"Email {self.email.id} missing summary title "
                f"for issue creation"
            )
            return False

        # Check if email has been properly processed (has LLM content)
        if not self.email.llm_content or not self.email.llm_content.strip():
            logger.error(
                f"Email {self.email.id} missing LLM content, "
                f"may not have been fully processed"
            )
            return False

        logger.debug(f"Email {self.email.id} content validation passed")
        return True

    def _set_processing_status(self) -> None:
        """
        Set the email to issue processing status.
        Only set if current status allows the transition.
        """
        # Check if we can transition to issue_processing
        if self.email.status == EmailStatus.ISSUE_SUCCESS.value:
            # Already in issue_success, skip status change
            logger.warning(
                f"[Issue] Email {self.email.id} already in "
                f"{self.email.status}, skipping status change"
            )
            return

        # Set to issue_processing only if allowed
        self._save_email(status=self.processing_status)

    def _execute_issue_creation(self, force_mode: bool = False) -> Dict:
        """
        Execute issue creation for the email.

        Args:
            force_mode: Whether to force processing regardless of existing
                       issues

        Returns:
            Dict: Issue creation results
        """
        try:
            # Get issue configuration (already validated in _is_already_complete)
            issue_config = self._get_issue_config()

            # Issue creation is enabled, create pending Issue
            issue = self._create_pending_issue(issue_config)
            logger.info(f"[{self.task_name}] Created pending issue "
                       f"{issue.id} for email {self.email_id}")

            # Process with JIRA if engine is jira
            if issue.engine == 'jira':
                try:
                    jira_result = self._process_with_jira(
                        issue, issue_config
                    )
                    logger.info(f"[{self.task_name}] JIRA processing "
                                f"completed for issue {issue.id}: "
                                f"{jira_result}")

                    return {
                        'success': True,
                        'issue_id': str(issue.id),
                        'engine': issue.engine,
                        'status': 'completed',
                        'jira_result': jira_result
                    }
                except Exception as e:
                    logger.error(f"[{self.task_name}] JIRA processing "
                                 f"failed for issue {issue.id}: {e}")
                    return {
                        'success': False,
                        'error': str(e),
                        'issue_id': str(issue.id)
                    }
            else:
                # For other engines, issue created successfully
                logger.info(f"[{self.task_name}] Issue {issue.id} created "
                           f"for engine {issue.engine}, will be processed "
                           f"by separate task")

                return {
                    'success': True,
                    'issue_id': str(issue.id),
                    'engine': issue.engine,
                    'status': 'created',
                    'message': f'Issue created for {issue.engine} engine'
                }

        except Exception as e:
            logger.error(f"[{self.task_name}] Error creating issue for "
                        f"email {self.email_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _update_email_status(self, results: Dict) -> None:
        """
        Update email status based on issue creation results.

        Args:
            results: Results from _execute_issue_creation
        """
        if results['success']:
            if results.get('status') == 'completed':
                # JIRA processing completed
                self._save_email(status=EmailStatus.COMPLETED.value)
            else:
                # Issue created but not processed yet
                self._save_email(status=self.next_success_status)
        else:
            error_message = results.get('error', 'Issue creation failed')
            self._save_email(status=self.next_failed_status,
                           error_message=error_message)

    def _handle_issue_error(self, exc: Exception) -> None:
        """
        Handle issue creation errors.

        Args:
            exc: The exception that occurred
        """
        error_message = str(exc)
        self._save_email(status=self.next_failed_status,
                       error_message=error_message)
        logger.error(f"[{self.task_name}] Error handled for email "
                    f"{self.email_id}: {error_message}")

    def _get_issue_config(self) -> Dict[str, Any]:
        """
        Get issue configuration from user settings using the generic method.

        Returns:
            Dict: Issue configuration or None if not found
        """
        try:
            return Settings.get_user_config(self.email.user, 'issue_config')
        except ValueError:
            logger.info(f"[{self.task_name}] No issue_config found for "
                        f"user {self.email.user}")
            return None

    def _get_engine_config(self, engine_name: str) -> Dict[str, Any]:
        """
        Get engine configuration from issue_config based on engine name.

        Args:
            engine_name: Name of the engine (e.g., 'jira', 'email', 'slack')

        Returns:
            Dict: Engine configuration or None if not found
        """
        issue_config = self._get_issue_config()
        if not issue_config:
            return None

        engine_config = issue_config.get(engine_name, {})
        if not engine_config:
            logger.info(f"[{self.task_name}] No {engine_name} "
                        f"configuration in issue_config for user "
                        f"{self.email.user}")
            return None

        return engine_config

    def _create_pending_issue(self, issue_config: Dict[str, Any]) -> Issue:
        """
        Create a pending Issue object for the email.

        Args:
            issue_config: Issue configuration dictionary

        Returns:
            Issue: The created issue object
        """
        # Get engine configuration
        engine_name = issue_config.get('engine', 'jira')

        # Create issue (no status field needed)
        issue = Issue.objects.create(
            user=self.email.user,
            email_message=self.email,
            title=self.email.summary_title or 'Email Issue',
            description=self.email.summary_content or 'No content',
            priority=issue_config.get('jira', {}).get(
                'default_priority', 'Medium'
            ),
            engine=engine_name,
            metadata={
                'config': issue_config,
                'email_id': str(self.email.id),
                'created_from': 'issue_task'
            }
        )

        logger.info(f"[{self.task_name}] Created pending issue "
                    f"{issue.id} with engine {engine_name}")

        return issue

    def _process_with_jira(
        self,
        issue: Issue,
        issue_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process issue with JIRA integration.

        Args:
            issue: Issue object to process
            issue_config: Issue configuration dictionary

        Returns:
            Dict: JIRA processing results
        """
        try:
            # Get JIRA configuration using the generic method
            jira_config = self._get_engine_config('jira')
            if not jira_config:
                raise ValueError("JIRA configuration not found")

            # Create JIRA handler
            jira_handler = JiraIssueHandler(jira_config)

            # Create JIRA issue
            issue_key = jira_handler.create_issue(issue, self.email, self.force)
            logger.info(
                f"[Issue] Created JIRA issue {issue_key} for issue {issue.id}"
            )

            # Upload attachments
            upload_result = jira_handler.upload_attachments(
                issue_key, self.email
            )
            logger.info(
                f"[Issue] Uploaded {upload_result['uploaded_count']} "
                f"attachments to JIRA issue {issue_key}"
            )

            # Update issue with external ID and URL
            issue.external_id = issue_key
            issue.issue_url = f"{jira_config['url']}/browse/{issue_key}"
            issue.metadata.update({
                'upload_result': upload_result
            })
            issue.save(update_fields=['external_id', 'issue_url', 'metadata'])

            return {
                'issue_key': issue_key,
                'jira_url': f"{jira_config['url']}/browse/{issue_key}",
                'upload_result': upload_result
            }

        except Exception as e:
            logger.error(f"[{self.task_name}] JIRA processing failed: {e}")
            raise



    def _save_email(self, status: str = "", error_message: str = "") -> None:
        """
        Save email status and error message.

        Args:
            status: Status to set
            error_message: Error message to set
        """
        update_fields = []

        if status:
            self.email.status = status
            update_fields.append('status')

        if error_message:
            self.email.error_message = error_message
            update_fields.append('error_message')
        elif status:  # Clear error message when setting new status
            self.email.error_message = ""
            update_fields.append('error_message')

        if update_fields:
            self.email.save(update_fields=update_fields)
            logger.info(f"[{self.task_name}] Saved email {self.email_id} "
                       f"to {status}")


# Create IssueCreateTask instance for Celery task registration
issue_create_task_instance = IssueCreateTask()


@shared_task
def create_issue_task(
    email_id: str,
    force: bool = False,
    *args,
    **kwargs
) -> str:
    """
    Celery task for creating issues from email summaries.

    This is a compatibility wrapper around the IssueCreateTask class.

    Args:
        email_id (str): ID of the email to process
        force (bool): Whether to force processing regardless of current status.
                     When True, skips status checks and allows reprocessing
                     even if the issue already exists.
        *args: Additional positional arguments (ignored)
        **kwargs: Additional keyword arguments (ignored)

    Returns:
        str: The email_id for the next task in the chain
    """
    return issue_create_task_instance.run(email_id, force)


def test_issue_task_logic(email_id: str) -> Dict[str, Any]:
    """
    Test function to validate issue task logic without Celery.

    This function can be used for testing and debugging the issue creation
    logic without running the full Celery task.

    Args:
        email_id (str): ID of the email to test

    Returns:
        Dict: Test results and any created issues
    """
    try:
        # Create task instance
        task = IssueCreateTask()

        # Initialize task
        task.before_start(email_id, force=False)

        # Run pre-execution checks
        pre_check = task._pre_execution_check()
        already_complete = task._is_already_complete()
        content_valid = task._validate_required_content()

        # Get issue config
        issue_config = task._get_issue_config()

        return {
            'email_id': email_id,
            'email_status': task.email.status,
            'pre_execution_check': pre_check,
            'already_complete': already_complete,
            'content_valid': content_valid,
            'issue_config': issue_config,
            'can_proceed': pre_check and not already_complete and content_valid
        }

    except Exception as e:
        return {
            'email_id': email_id,
            'error': str(e),
            'can_proceed': False
        }
