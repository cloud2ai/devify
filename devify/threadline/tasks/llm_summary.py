"""
LLM Summary Task using Celery Task class approach.

ARCHITECTURE DESIGN
==================

This module implements the fourth stage of the email processing pipeline,
following the same clean architecture pattern as OCR task with proper
state machine integration and centralized force logic handling.

State Machine Integration
------------------------

Allowed Input States:
  - LLM_EMAIL_SUCCESS: Previous LLM email processing completed
    successfully
  - LLM_SUMMARY_FAILED: Previous summary attempt failed, allows retry

Status Transitions:
  - LLM_EMAIL_SUCCESS/LLM_SUMMARY_FAILED → LLM_SUMMARY_PROCESSING →
    LLM_SUMMARY_SUCCESS (normal flow)
  - LLM_EMAIL_SUCCESS/LLM_SUMMARY_FAILED → LLM_SUMMARY_PROCESSING →
    LLM_SUMMARY_FAILED (error flow)

Processing Logic
---------------
- Generates summary content and title using LLM
- Combines email content with attachment OCR content
- Skips processing if summary already exists (unless force=True)
- Uses user-configured summary prompts for LLM processing
- Handles both summary content and title generation

Force Mode Behavior
------------------
- Bypasses all status checks and validations
- Skips status updates to prevent state machine corruption
- Allows reprocessing regardless of current state
- Processes all image attachments regardless of OCR status
- Regenerates summary even if content already exists

This implementation follows the established design pattern for consistent
task architecture across the email processing pipeline.
"""


# Import statements
from celery import Task, shared_task
import logging
from typing import Dict, Any
from django.conf import settings

from threadline.models import EmailMessage, Settings
from threadline.utils.summary import call_llm
from threadline.state_machine import EmailStatus

logger = logging.getLogger(__name__)


class LLMSummaryTask(Task):
    """
    LLM Summary generation task using Celery Task class.

    This class provides a unified execution flow for summary generation
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
        self.task_name = "LLM_SUMMARY"

        # For EmailMessage Status Control
        self.allowed_statuses = [
            EmailStatus.LLM_EMAIL_SUCCESS.value,   # Previous step success
            EmailStatus.LLM_SUMMARY_FAILED.value  # Current step failed
                                                  # (retry)
        ]
        self.next_success_status = EmailStatus.LLM_SUMMARY_SUCCESS.value
        self.processing_status = EmailStatus.LLM_SUMMARY_PROCESSING.value
        self.next_failed_status = EmailStatus.LLM_SUMMARY_FAILED.value

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

            # Step 3: Validate LLM content (skip in force mode)
            if not self.force and not self.email.llm_content:
                raise ValueError(f"Email {email_id} LLM content is missing "
                               f"for summary generation.")

            # Step 4: Set processing status (skip in force mode)
            if not self.force:
                logger.info(f"[{self.task_name}] Setting processing "
                           f"status for email {email_id}")
                self._set_processing_status()

            # Step 5: Execute core business logic
            summary_results = self._execute_summary_generation(
                force_mode=self.force)

            # Step 6: Update email status (skip in force mode)
            if not self.force:
                self._update_email_status(summary_results)
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
                self._handle_summary_error(exc)
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
        Check if summary generation is already complete.

        Returns:
            bool: True if already complete
        """
        if self.current_status == self.next_success_status:
            logger.info(f"[{self.task_name}] Email {self.email_id} already "
                       f"in {self.next_success_status} state, skipping to "
                       f"next task")
            return True

        # Check if content exists but status is incorrect
        if (self.email.summary_content and self.email.summary_title and
            self.current_status != self.next_success_status):
            logger.info(f"[{self.task_name}] Email {self.email_id} has "
                       f"summary content but incorrect status, updating")
            self._save_email(status=self.next_success_status)
            return True

        return False

    def _set_processing_status(self) -> None:
        """
        Set the email to processing status.
        """
        self._save_email(status=self.processing_status)

    def _execute_summary_generation(self, force_mode: bool = False) -> Dict:
        """
        Execute summary generation for the email.

        Args:
            force_mode: Whether to force processing regardless of existing
                       content

        Returns:
            Dict: Summary generation results
        """
        # Get prompt configuration
        prompt_config = Settings.get_user_prompt_config(
            self.email.user, ['summary_prompt', 'summary_title_prompt']
        )
        summary_prompt = prompt_config['summary_prompt']
        summary_title_prompt = prompt_config['summary_title_prompt']
        output_language = prompt_config.get(
            'output_language',
            settings.LLM_OUTPUT_LANGUAGE
        )

        content = f"Subject: {self.email.subject}\nText Content: " \
                  f"{self.email.llm_content}\n"

        # Collect all OCR processed content from attachments with filenames
        # In force mode: process all image attachments
        # In normal mode: only process attachments with LLM content
        ocr_contents = []
        if force_mode:
            # Force mode: process all image attachments regardless of status
            image_attachments = self.email.attachments.filter(is_image=True)
        else:
            # Normal mode: only process attachments with LLM content
            image_attachments = self.email.attachments.filter(
                is_image=True
            ).exclude(llm_content__isnull=True).exclude(llm_content="")

        for att in image_attachments:
            if att.llm_content and att.llm_content.strip():
                ocr_contents.append(
                    f"[Attachment: {att.safe_filename}]\n{att.llm_content}")

        # Combine email content with OCR contents
        combined_content = content
        if ocr_contents:
            combined_content += "\n\n--- ATTACHMENT OCR CONTENT ---\n\n"
            combined_content += "\n\n".join(ocr_contents)
            logger.info(f"[{self.task_name}] Included {len(ocr_contents)} "
                       f"OCR contents in summary")
        else:
            logger.info(f"[{self.task_name}] No attachment OCR content "
                       f"available for summary")

        # Generate summary content and title
        summary_content = self.email.summary_content
        summary_title = self.email.summary_title

        if not summary_content or force_mode:
            summary_content = call_llm(
                summary_prompt,
                combined_content,
                output_language
            )

        if not summary_title or force_mode:
            summary_title = call_llm(
                summary_title_prompt,
                combined_content,
                output_language
            )

        summary_content = summary_content.strip() if summary_content else ''
        summary_title = summary_title.strip() if summary_title else ''

        # Save content regardless of mode
        self._save_summary_content(summary_content, summary_title)

        return {
            'success': True,
            'summary_content': summary_content,
            'summary_title': summary_title,
            'ocr_contents_count': len(ocr_contents),
            'content_length': len(summary_content) + len(summary_title)
        }

    def _update_email_status(self, results: Dict) -> None:
        """
        Update email status based on summary generation results.

        Args:
            results: Results from _execute_summary_generation
        """
        if results['success']:
            self._save_email(status=self.next_success_status)
        else:
            error_message = f"Summary generation failed"
            self._save_email(status=self.next_failed_status,
                           error_message=error_message)

    def _save_summary_content(self, summary_content: str,
                            summary_title: str) -> None:
        """
        Save summary content and title to email.

        Args:
            summary_content: Generated summary content
            summary_title: Generated summary title
        """
        update_fields = []

        if summary_content:
            self.email.summary_content = summary_content
            update_fields.append('summary_content')

        if summary_title:
            self.email.summary_title = summary_title
            update_fields.append('summary_title')

        if update_fields:
            self.email.save(update_fields=update_fields)
            logger.info(f"[{self.task_name}] Saved summary content for "
                       f"email {self.email_id}")

    def _handle_summary_error(self, exc: Exception) -> None:
        """
        Handle summary generation errors.

        Args:
            exc: The exception that occurred
        """
        error_message = str(exc)
        self._save_email(status=self.next_failed_status,
                       error_message=error_message)
        logger.error(f"[{self.task_name}] Error handled for email "
                    f"{self.email_id}: {error_message}")

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


# Create LLMSummaryTask instance for Celery task registration
llm_summary_task_instance = LLMSummaryTask()


@shared_task
def summarize_email_task(
    email_id: str,
    force: bool = False,
    *args,
    **kwargs
) -> str:
    """
    Celery task for generating email summary and title using LLM.

    This is a compatibility wrapper around the LLMSummaryTask class.

    Args:
        email_id (str): ID of the email to process
        force (bool): Whether to force processing regardless of current status.
                     When True, skips status checks and allows reprocessing
                     even if the content already exists.
        *args: Additional positional arguments (ignored)
        **kwargs: Additional keyword arguments (ignored)

    Returns:
        str: The email_id for the next task in the chain
    """
    return llm_summary_task_instance.run(email_id, force)
