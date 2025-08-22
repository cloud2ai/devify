"""
LLM Email Body Task using Celery Task class approach.

This module follows the same architecture pattern as ocr.py:
- Task class with before_start() for initialization
- run() method for main execution flow
- Helper methods for specific logic
- Compatibility wrapper function for existing calls

See ocr.py for detailed architecture documentation.
"""


# Import statements
from celery import Task, shared_task
import logging
from typing import Dict, Any
from django.core.exceptions import ValidationError

from jirabot.models import EmailMessage, Settings
from jirabot.utils.summary import call_llm
from jirabot.state_machine import EmailStatus

logger = logging.getLogger(__name__)


class EmailBodyTask(Task):
    """
    LLM Email body organization task using Celery Task class.

    This class provides a unified execution flow for email body processing
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
        self.task_name = "EmailBody"
        self.allowed_statuses = [
            EmailStatus.OCR_SUCCESS.value,
            EmailStatus.SUMMARY_FAILED.value
        ]

        # Get email object
        try:
            self.email = EmailMessage.objects.select_related(
                'user'
            ).get(id=email_id)
            logger.info(f"[EmailBody] Email object retrieved: {email_id}")
        except EmailMessage.DoesNotExist:
            logger.error(f"[EmailBody] EmailMessage {email_id} not found")
            raise

        logger.info(f"[EmailBody] Initialization completed for {email_id}, "
                    f"force: {force}")

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
            # Initialize task
            #
            # Normal flow: Celery automatically calls before_start before run
            # Manual testing: Directly calling run method
            #   Check self.email doesn't exist → Call self.before_start to
            #   complete initialization
            #   Continue with business logic
            if not hasattr(self, 'email'):
                self.before_start(email_id, force)

            logger.info(f"[EmailBody] Start processing: {email_id}, "
                        f"force: {force}")

            # Step 1: Pre-execution check (status machine + force parameter)
            if not self._pre_execution_check():
                logger.info(f"[EmailBody] Pre-execution check failed, "
                            f"skipping to next task: {email_id}")
                return email_id

            # Step 2: Check if already complete
            if self._is_already_complete():
                return email_id

            # Step 3: Set processing status
            self._set_processing_status()

            # Step 4: Validate email content
            if not self._validate_email_content():
                raise ValueError("No email content available for LLM "
                                 "organization.")

            # Step 5: Execute core business logic and complete task
            processing_results = self._execute_email_processing()

            logger.info(f"[EmailBody] Email body organization task completed: "
                        f"{email_id}")
            return email_id

        except EmailMessage.DoesNotExist:
            logger.error(f"[EmailBody] EmailMessage {email_id} not found")
            raise
        except Exception as exc:
            logger.error(f"[EmailBody] Fatal error for {email_id}: {exc}")
            # Save error status to email (force mode handling is inside
            # _save_email)
            self._save_email(
                status=EmailStatus.SUMMARY_FAILED.value,
                error_message=str(exc)
            )
            raise

    def _pre_execution_check(self) -> bool:
        """
        Pre-execution check: Check if the task can be executed based on
        current status and force parameter.

        This is the main pre-execution check that combines:
        - Status machine validation
        - Force parameter handling

        Returns:
            bool: True if execution is allowed
        """
        if self.force:
            logger.debug(f"[EmailBody] Force mode enabled for email "
                         f"{self.email.id}, skipping status check")
            return True

        if self.email.status not in self.allowed_statuses:
            logger.warning(
                f"Email {self.email.id} cannot be processed in status: "
                f"{self.email.status}. Allowed: {self.allowed_statuses}"
            )
            return False

        logger.debug(f"[EmailBody] Pre-execution check passed for email "
                     f"{self.email.id}")
        return True

    def _is_already_complete(self) -> bool:
        """
        Check if email body processing is already complete.

        Returns:
            bool: True if already complete
        """
        if self.force:
            logger.debug(f"[EmailBody] Force mode enabled for email "
                         f"{self.email.id}, skipping completion check")
            return False

        if self.email.llm_content:
            logger.info(
                f"Email {self.email.id} already has LLM content, "
                f"skipping to next task"
            )
            return True

        return False

    def _validate_email_content(self) -> bool:
        """
        Validate that email has content for LLM processing.

        Returns:
            bool: True if email content exists
        """
        # Prefer text_content > html_content > raw_content
        content = self.email.text_content

        if not content or not content.strip():
            logger.error(f"Email {self.email.id} has no content available for "
                         f"LLM organization")
            return False
        return True

    def _set_processing_status(self) -> None:
        """
        Set the email to processing status.
        """
        self._save_email(status=EmailStatus.SUMMARY_PROCESSING.value)

    def _execute_email_processing(self) -> Dict:
        """
        Execute email body processing using LLM.

        Returns:
            Dict: Email processing results
        """
        # Prefer text_content > html_content > raw_content
        content = self.email.text_content

        # Get prompt configuration
        prompt_config = Settings.get_user_prompt_config(
            self.email.user, ['email_content_prompt']
        )
        email_content_prompt = prompt_config['email_content_prompt']

        # Call LLM to organize email content
        llm_result = call_llm(email_content_prompt, content)
        llm_content = llm_result.strip() if llm_result else ''

        # Save llm_content and update status (force mode handling is
        # inside _save_email)
        self._save_email(
            status=EmailStatus.SUMMARY_SUCCESS.value,
            llm_content=llm_content
        )

        logger.info(
            f"[EmailBody] Email body organization completed: {self.email.id}"
        )

        return {
            'llm_content': llm_content,
            'content_length': len(llm_content) if llm_content else 0
        }

    def _save_email(
        self,
        status: str = "",
        llm_content: str = "",
        error_message: str = ""
    ) -> None:
        """
        Save email with status, error message, and optionally llm_content.
        In force mode, only save llm_content, skip status updates.

        Args:
            status: Status to set (only used in non-force mode)
            error_message: Error message to set (only used in non-force mode)
            llm_content: LLM content to save (always saved)
        """
        # Always save llm_content if provided (this is the main purpose of
        # force mode)
        update_fields = []
        if llm_content is not None:
            self.email.llm_content = llm_content
            update_fields.append('llm_content')

        if self.force:
            # Force mode: only save content, skip status updates
            self.email.save(update_fields=update_fields)
            logger.debug(f"[EmailBody] Force mode: saved content for email "
                         f"{self.email.id}")
            return

        # Non-force mode: save everything
        self.email.status = status
        if error_message:
            self.email.error_message = error_message
        else:
            self.email.error_message = ""  # Clear any previous error

        update_fields.extend(['status', 'error_message'])
        self.email.save(update_fields=update_fields)
        logger.debug(f"[EmailBody] Saved email {self.email.id} to {status}")


# Create EmailBodyTask instance for Celery task registration
email_body_task = EmailBodyTask()


@shared_task(bind=True)
def organize_email_body_task(self, email_id: str, force: bool = False) -> str:
    """
    Celery task for organizing email body content using LLM.

    This is a compatibility wrapper around the EmailBodyTask class.

    Args:
        email_id (str): ID of the email to process
        force (bool): Whether to force processing regardless of current status.
                     When True, skips status checks and allows reprocessing
                     even if the content already exists.

    Returns:
        str: The email_id for the next task in the chain
    """
    return email_body_task.run(email_id, force)
