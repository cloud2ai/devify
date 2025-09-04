"""
LLM Email Body Task using Celery Task class approach.

ARCHITECTURE DESIGN
==================

This module implements the third stage of the email processing pipeline,
following the same clean architecture pattern as OCR task with proper
state machine integration and centralized force logic handling.

State Machine Integration
------------------------

Allowed Input States:
  - LLM_OCR_SUCCESS: Previous LLM OCR processing completed successfully
  - LLM_EMAIL_FAILED: Previous LLM email attempt failed, allows retry

Status Transitions:
  - LLM_OCR_SUCCESS/LLM_EMAIL_FAILED → LLM_EMAIL_PROCESSING →
    LLM_EMAIL_SUCCESS (normal flow)
  - LLM_OCR_SUCCESS/LLM_EMAIL_FAILED → LLM_EMAIL_PROCESSING →
    LLM_EMAIL_FAILED (error flow)

Processing Logic
---------------
- Processes email text content using LLM
- Skips processing if LLM content already exists (unless force=True)
- Uses user-configured email content prompt for LLM processing
- Saves empty string for failed LLM attempts
- Prefers text_content over html_content over raw_content

Force Mode Behavior
------------------
- Bypasses all status checks and validations
- Skips status updates to prevent state machine corruption
- Allows reprocessing regardless of current state
- Processes email content regardless of existing LLM content

This implementation follows the established design pattern for consistent
task architecture across the email processing pipeline.
"""


# Import statements
from celery import Task, shared_task
from django.conf import settings
from django.core.exceptions import ValidationError
import logging
import re
from typing import Dict, Any

from threadline.models import EmailMessage, Settings
from threadline.utils.summary import call_llm
from threadline.state_machine import EmailStatus

logger = logging.getLogger(__name__)


class LLMEmailTask(Task):
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
        self.task_name = "LLM_EMAIL"

        # For EmailMessage Status Control
        self.allowed_statuses = [
            EmailStatus.LLM_OCR_SUCCESS.value,    # Previous step success
            EmailStatus.LLM_EMAIL_FAILED.value   # Current step failed
                                                 # (retry)
        ]
        self.next_success_status = EmailStatus.LLM_EMAIL_SUCCESS.value
        self.processing_status = EmailStatus.LLM_EMAIL_PROCESSING.value
        self.next_failed_status = EmailStatus.LLM_EMAIL_FAILED.value

        # Get email object
        try:
            self.email = EmailMessage.objects.select_related(
                'user'
            ).get(id=email_id)
            # Force refresh to get latest status from database
            self.email.refresh_from_db()
            # Cache the current status for consistent use throughout the task
            self.current_status = self.email.status
            logger.info(f"[{self.task_name}] Email object retrieved: "
                       f"{email_id}, current_status: {self.current_status}")
        except EmailMessage.DoesNotExist:
            logger.error(f"[{self.task_name}] EmailMessage {email_id} "
                         f"not found")
            raise

        logger.info(f"[{self.task_name}] Initialization completed for "
                    f"{email_id}, force: {force}")

    def run(self, email_id: str, force: bool = False) -> str:
        """
        Main task execution method with centralized force logic.

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

            # Step 3: Validate email content
            if not self._validate_email_content():
                raise ValueError("No email content available for LLM "
                                 "organization.")

            # Step 4: Set processing status (skip in force mode)
            if not self.force:
                logger.info(f"[{self.task_name}] Setting processing "
                            f"status for email {email_id}")
                self._set_processing_status()

            # Step 5: Execute core business logic (always execute, pass
            # force_mode parameter)
            logger.info(f"[{self.task_name}] Processing email content, "
                        f"force: {self.force}")
            processing_results = self._execute_email_processing(
                force_mode=self.force)

            # Step 6: Update email status (skip in force mode)
            if not self.force:
                logger.info(f"[{self.task_name}] Updating email status "
                            f"for email {email_id}")
                self._update_email_status(processing_results)
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
            logger.error(f"[{self.task_name}] Fatal error for "
                         f"{email_id}: {exc}")
            if not self.force:
                self._handle_email_error(exc)
            else:
                logger.warning(f"[{self.task_name}] Force mode: "
                               f"skipping error handling for {email_id}")
            raise

    def _pre_execution_check(self) -> bool:
        """
        Pre-execution check: validate email status.

        Returns:
            bool: True if email status allows processing
        """
        if self.current_status not in self.allowed_statuses:
            logger.warning(
                f"[{self.task_name}] Email {self.email_id} cannot be "
                f"processed in status: {self.current_status}. Allowed: "
                f"{self.allowed_statuses}")
            return False

        logger.debug(f"[{self.task_name}] Pre-execution check passed "
                     f"for email {self.email_id}")
        return True

    def _is_already_complete(self) -> bool:
        """
        Check if LLM email processing is already complete.

        Returns:
            bool: True if already complete
        """
        if self.current_status == self.next_success_status:
            logger.info(
                f"[{self.task_name}] Email {self.email_id} already in "
                f"{self.next_success_status} state, skipping to next task"
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
            logger.error(f"[{self.task_name}] Email {self.email_id} has "
                         f"no content available for LLM organization")
            return False
        return True

    def _set_processing_status(self) -> None:
        """
        Set the email to processing status.
        """
        self._save_email(status=self.processing_status)

    def _execute_email_processing(self, force_mode: bool = False) -> Dict:
        """
        Execute LLM processing for email content.

        Args:
            force_mode: If True, reprocess content; if False, skip existing content

        Returns:
            Dict: LLM processing results
        """
        # Check if we should skip processing based on mode
        if not force_mode and self.email.llm_content:
            logger.info(f"[{self.task_name}] Email {self.email_id} "
                        f"already has LLM content, skipping in normal mode")
            return {
                'success': True,
                'skipped': True,
                'reason': 'Already has LLM content',
                'content_length': len(self.email.llm_content)
            }

        # Prefer text_content > html_content > raw_content
        content = self.email.text_content

        # Replace image placeholders with actual OCR content
        content = self._replace_image_placeholders_with_ocr(content)

        # Get prompt configuration
        prompt_config = Settings.get_user_prompt_config(
            self.email.user, ['email_content_prompt']
        )
        email_content_prompt = prompt_config['email_content_prompt']
        output_language = prompt_config.get(
            'output_language',
            settings.LLM_OUTPUT_LANGUAGE
        )

        try:
            # Call LLM to organize email content
            logger.info(f"[{self.task_name}] Processing email content "
                        f"for email {self.email_id}")

            llm_result = call_llm(
                email_content_prompt,
                content,
                output_language
            )
            llm_content = llm_result.strip() if llm_result else ''

            # Save LLM result
            if llm_content:
                logger.info(f"LLM email processing successful for "
                           f"email {self.email_id}")
                self._save_email_content(llm_content)
                return {
                    'success': True,
                    'skipped': False,
                    'content_length': len(llm_content)
                }
            else:
                logger.warning(f"LLM email processing completed for "
                               f"email {self.email_id} - no content generated")
                self._save_email_content('')
                return {
                    'success': True,
                    'skipped': False,
                    'content_length': 0
                }

        except Exception as e:
            logger.error(f"LLM email processing failed for "
                         f"email {self.email_id}: {e}")
            # Save empty LLM content for failed processing
            self._save_email_content('')
            return {
                'success': False,
                'error': str(e),
                'skipped': False
            }

    def _update_email_status(self, email_results: Dict) -> None:
        """
        Update email status based on LLM processing results.
        This is called after email content has been processed.

        Args:
            email_results: Results from LLM processing
        """
        if email_results.get('skipped'):
            # Content already exists, mark as success
            self._save_email(status=self.next_success_status)
            logger.info(f"[{self.task_name}] LLM email completed for "
                        f"email {self.email_id}: skipped (already had content)")
        elif email_results['success']:
            # Processing successful
            self._save_email(status=self.next_success_status)
            logger.info(f"[{self.task_name}] LLM email completed for "
                        f"email {self.email_id}: successful")
        else:
            # Processing failed
            error_message = f"LLM email processing failed: {email_results['error']}"
            self._save_email(
                status=self.next_failed_status,
                error_message=error_message
            )
            logger.error(f"[{self.task_name}] LLM email failed for "
                         f"email {self.email_id}: {error_message}")

    def _replace_image_placeholders_with_ocr(self, content: str) -> str:
        """
        Replace [IMAGE: filename] placeholders with actual OCR content.

        This method finds all image placeholders in the content and replaces
        them with the corresponding LLM-processed OCR content from attachments.

        Args:
            content: Email content with image placeholders

        Returns:
            str: Content with image placeholders replaced by OCR content
        """
        # Find all image placeholders in the content
        image_placeholder_pattern = r'\[IMAGE:\s*([^\]]+)\]'
        placeholders = re.findall(image_placeholder_pattern, content)

        if not placeholders:
            logger.debug(f"[{self.task_name}] No image placeholders found "
                        f"in email {self.email_id}")
            return content

        logger.info(f"[{self.task_name}] Found {len(placeholders)} image "
                   f"placeholders in email {self.email_id}: {placeholders}")

        # Get all image attachments with LLM content
        image_attachments = self.email.attachments.filter(
            is_image=True
        ).exclude(llm_content__isnull=True).exclude(llm_content="")

        # Create mapping of safe_filename -> llm_content
        ocr_content_map = {}
        for att in image_attachments:
            if att.llm_content and att.llm_content.strip():
                safe_filename = att.safe_filename or att.filename
                if safe_filename:
                    ocr_content_map[safe_filename] = att.llm_content.strip()
                    logger.debug(f"[{self.task_name}] Mapped {safe_filename} "
                               f"to OCR content ({len(att.llm_content)} chars)")

        logger.info(f"[{self.task_name}] Created OCR content map with "
                   f"{len(ocr_content_map)} entries")

        # Replace placeholders with OCR content
        def replace_placeholder(match):
            placeholder_filename = match.group(1).strip()

            if placeholder_filename in ocr_content_map:
                ocr_content = ocr_content_map[placeholder_filename]
                logger.debug(f"[{self.task_name}] Replacing placeholder "
                           f"[IMAGE: {placeholder_filename}] with OCR content")
                return f"\n\n[IMAGE: {placeholder_filename}]\n{ocr_content}\n\n"
            else:
                logger.warning(f"[{self.task_name}] No OCR content found "
                             f"for placeholder: {placeholder_filename}")
                return f"[IMAGE: {placeholder_filename}] (OCR content not found)"

        # Replace all placeholders
        result_content = re.sub(
            image_placeholder_pattern,
            replace_placeholder,
            content
        )

        logger.info(f"[{self.task_name}] Replaced image placeholders in "
                   f"email {self.email_id}, content length: "
                   f"{len(content)} -> {len(result_content)}")

        return result_content

    def _save_email_content(self, llm_content: str) -> None:
        """
        Save email LLM content.
        This method is pure - only saves content, no status logic.

        Args:
            llm_content: LLM content to save
        """
        self.email.llm_content = llm_content
        self.email.save(update_fields=['llm_content'])
        logger.debug(f"[{self.task_name}] Saved LLM content for "
                     f"email {self.email_id}")

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
            logger.info(f"[{self.task_name}] Saved email "
                        f"{self.email_id} to {status}")

    def _handle_email_error(self, exc: Exception) -> None:
        """
        Handle LLM email processing errors by updating email status.
        Only called in normal mode.

        Args:
            exc: Exception that occurred
        """
        try:
            self._save_email(
                status=self.next_failed_status,
                error_message=str(exc)
            )
        except Exception:
            logger.error(f"[{self.task_name}] Failed to set status "
                         f"for {self.email_id}")


# Create LLMEmailTask instance for Celery task registration
llm_email_task_instance = LLMEmailTask()


@shared_task
def llm_email_task(
    email_id: str,
    force: bool = False,
    *args,
    **kwargs
) -> str:
    """
    Celery task for organizing email body content using LLM.

    This is a compatibility wrapper around the LLMEmailTask class.

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
    return llm_email_task_instance.run(email_id, force)
