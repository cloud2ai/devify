"""
LLM Attachment OCR Task using Celery Task class approach.

ARCHITECTURE DESIGN
==================

This module implements the second stage of the email processing pipeline,
following the same clean architecture pattern as OCR task with proper
state machine integration and centralized force logic handling.

State Machine Integration
------------------------

Allowed Input States:
  - OCR_SUCCESS: Previous OCR processing completed successfully
  - LLM_OCR_FAILED: Previous LLM OCR attempt failed, allows retry

Status Transitions:
  - OCR_SUCCESS/LLM_OCR_FAILED → LLM_OCR_PROCESSING → LLM_OCR_SUCCESS
    (normal flow)
  - OCR_SUCCESS/LLM_OCR_FAILED → LLM_OCR_PROCESSING → LLM_OCR_FAILED
    (error flow)

Processing Logic
---------------
- Processes only image attachments with existing OCR content
- Skips attachments that already have LLM content (unless force=True)
- Uses user-configured OCR prompt for LLM processing
- Saves empty string for failed LLM attempts
- Handles non-image attachments by skipping LLM processing

Force Mode Behavior
------------------
- Bypasses all status checks and validations
- Skips status updates to prevent state machine corruption
- Allows reprocessing regardless of current state
- Processes all image attachments regardless of existing LLM content

This implementation follows the established design pattern for consistent
task architecture across the email processing pipeline.
"""

import logging
from typing import Dict, Any
from django.core.exceptions import ValidationError
from django.conf import settings

from celery import Task, shared_task

from threadline.models import EmailMessage, Settings
from threadline.utils.summary import call_llm
from threadline.state_machine import EmailStatus

logger = logging.getLogger(__name__)


class LLMOCRTask(Task):
    """
    LLM Attachment OCR organization task using Celery Task class.

    This class provides a unified execution flow for attachment processing
    while keeping all logic visible and maintainable.

    Note: This task now works without attachment status fields, using
    content-based logic instead.
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
        self.task_name = "LLM_OCR"

        # For EmailMessage Status Control
        self.allowed_statuses = [
            EmailStatus.OCR_SUCCESS.value,        # Previous step success
            EmailStatus.LLM_OCR_FAILED.value     # Current step failed (retry)
        ]
        self.next_success_status = EmailStatus.LLM_OCR_SUCCESS.value
        self.processing_status = EmailStatus.LLM_OCR_PROCESSING.value
        self.next_failed_status = EmailStatus.LLM_OCR_FAILED.value

        # Get email object
        try:
            self.email = EmailMessage.objects.select_related(
                'user'
            ).get(
                id=email_id
            )
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
                logger.info(f"[{self.task_name}] Pre-execution check failed, "
                            f"skipping to next task: {email_id}")
                return email_id

            # Step 2: Check if already complete (skip in force mode)
            if not self.force and self._is_already_complete():
                logger.info(f"[{self.task_name}] Email {email_id} already "
                            f"complete, skipping to next task")
                return email_id

            # Step 3: Set processing status (skip in force mode)
            if not self.force:
                logger.info(f"[{self.task_name}] Setting processing status "
                            f"for email {email_id}")
                self._set_processing_status()

            # Step 4: Process attachments (always execute, pass
            # force_mode parameter)
            image_attachments = self.email.attachments.filter(is_image=True)
            logger.info(f"[{self.task_name}] Processing "
                        f"{image_attachments.count()} image attachments, "
                        f"force: {self.force}")
            processing_results = self._execute_attachment_processing(
                image_attachments, force_mode=self.force)

            # Step 5: Update email status (skip in force mode)
            if not self.force:
                logger.info(f"[{self.task_name}] Updating email status "
                            f"for email {email_id}")
                self._update_email_status(processing_results)
            else:
                logger.info(f"[{self.task_name}] Force mode: skipping "
                            f"status updates for {email_id}")

            logger.info(f"[{self.task_name}] Processing completed: {email_id}")
            return email_id

        except EmailMessage.DoesNotExist:
            logger.error(f"[{self.task_name}] EmailMessage {email_id} "
                         f"not found")
            raise
        except Exception as exc:
            logger.error(f"[{self.task_name}] Fatal error for "
                         f"{email_id}: {exc}")
            if not self.force:
                self._handle_llm_error(exc)
            else:
                logger.warning(f"[{self.task_name}] Force mode: skipping "
                               f"error handling for {email_id}")
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
        Check if LLM OCR processing is already complete.

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

    def _set_processing_status(self) -> None:
        """
        Set email to processing status.
        """
        self._save_email(status=self.processing_status)

    def _execute_attachment_processing(
        self,
        image_attachments,
        force_mode: bool = False
    ) -> Dict:
        """
        Execute LLM processing for image attachments.

        Args:
            image_attachments: QuerySet of image attachments to process
            force_mode: If True, reprocess all attachments; if False, skip
                        existing content

        Returns:
            Dict: LLM processing results
        """
        if not image_attachments.exists():
            logger.info(f"[{self.task_name}] No image attachments to "
                        f"process for email {self.email_id}")
            return {
                'attachment_results': [],
                'success_count': 0,
                'fail_count': 0,
                'no_attachments': True
            }

        # Get prompt configuration
        prompt_config = Settings.get_user_prompt_config(
            self.email.user, ['ocr_prompt']
        )
        ocr_prompt = prompt_config['ocr_prompt']
        output_language = prompt_config.get(
            'output_language',
            settings.LLM_OUTPUT_LANGUAGE
        )

        attachment_results = []  # Store results for each attachment

        for attachment in image_attachments:
            # Check if we should skip this attachment based on mode
            if not force_mode and attachment.llm_content:
                logger.info(f"[{self.task_name}] Attachment "
                            f"{attachment.id} ({attachment.filename}) already "
                            f"has LLM content, skipping in normal mode")
                attachment_results.append({
                    'id': attachment.id,
                    'success': True,
                    'skipped': True,
                    'reason': 'Already has LLM content'
                })
                continue

            # Skip attachments with empty OCR content
            if not attachment.ocr_content or not attachment.ocr_content.strip():
                logger.warning(f"Attachment {attachment.id} "
                               f"({attachment.filename}) has no OCR content, "
                               f"skipping LLM organization")
                self._save_attachment(attachment, '')
                attachment_results.append({
                    'id': attachment.id,
                    'success': True,
                    'skipped': True,
                    'reason': 'No OCR content'
                })
                continue

            try:
                # Perform LLM processing
                logger.info(f"[{self.task_name}] Processing attachment "
                            f"{attachment.id} ({attachment.filename})")

                llm_result = call_llm(
                    ocr_prompt,
                    attachment.ocr_content,
                    output_language
                )
                llm_content = llm_result.strip() if llm_result else ''

                # Save LLM result
                if llm_content:
                    logger.info(f"LLM organization successful for attachment "
                               f"{attachment.id} ({attachment.filename})")
                    self._save_attachment(attachment, llm_content)
                    attachment_results.append({
                        'id': attachment.id,
                        'success': True,
                        'skipped': False
                    })
                else:
                    logger.warning(f"LLM organization completed for attachment "
                                   f"{attachment.id} ({attachment.filename}) "
                                   f"- no content generated")
                    self._save_attachment(attachment, '')
                    attachment_results.append({
                        'id': attachment.id,
                        'success': True,
                        'skipped': False
                    })

            except Exception as e:
                logger.error(f"LLM organization failed for attachment "
                             f"{attachment.id}: {e}")
                # Save empty LLM content for failed attachment
                self._save_attachment(attachment, '')
                attachment_results.append({
                    'id': attachment.id,
                    'success': False,
                    'error': str(e),
                    'skipped': False
                })

        # Handle non-image attachments - skip LLM processing
        non_image_attachments = self.email.attachments.filter(
            is_image=False
        )
        for attachment in non_image_attachments:
            # No LLM content to save for non-image attachments
            logger.info(f"[{self.task_name}] Non-image attachment "
                       f"{attachment.id} ({attachment.filename}) skipped "
                       f"LLM processing")

        # Calculate statistics
        success_count = sum(
            1 for r in attachment_results
            if r['success'] and not r['skipped']
        )
        fail_count = len([r for r in attachment_results if not r['success']])
        skipped_count = len([r for r in attachment_results if r['skipped']])

        return {
            'attachment_results': attachment_results,
            'success_count': success_count,
            'fail_count': fail_count,
            'skipped_count': skipped_count,
            'no_attachments': False
        }

    def _update_email_status(self, llm_results: Dict) -> None:
        """
        Update email status based on LLM processing results.
        This is called after all attachments have been processed.

        Args:
            llm_results: Results from LLM processing
        """
        if llm_results['no_attachments']:
            # No image attachments to process
            self._save_email(status=self.next_success_status)
            return

        if llm_results['fail_count'] == 0:
            # All attachments processed successfully (including skipped ones)
            self._save_email(status=self.next_success_status)

            # Log detailed results
            if llm_results.get('skipped_count', 0) > 0:
                logger.info(
                    f"[{self.task_name}] LLM OCR completed for email "
                    f"{self.email_id}: "
                    f"{llm_results['success_count']} processed, "
                    f"{llm_results['skipped_count']} skipped "
                    f"(already had content)"
                )
            else:
                logger.info(f"[{self.task_name}] LLM OCR completed for "
                            f"email {self.email_id}: "
                            f"{llm_results['success_count']} successful")
        else:
            # Some attachments failed
            failed_results = [
                result for result in llm_results['attachment_results']
                if not result['success']
            ]
            failed_files = ', '.join([
                f"attachment_{item['id']}({item['error']})"
                for item in failed_results
            ])
            error_message = (
                f'LLM OCR failed for {llm_results["fail_count"]} image '
                f'attachments: {failed_files}'
            )

            self._save_email(
                status=self.next_failed_status,
                error_message=error_message
            )
            logger.error(f"[{self.task_name}] LLM OCR failed for email "
                         f"{self.email_id}: {error_message}")

    def _save_attachment(self, attachment, llm_content: str = "") -> None:
        """
        Save attachment with LLM content.
        This method is pure - only saves attachment content, no status logic.

        Args:
            attachment: EmailAttachment object to save
            llm_content: LLM content to save
        """
        attachment.llm_content = llm_content
        attachment.save(update_fields=['llm_content'])
        logger.debug(f"[{self.task_name}] Saved LLM content for "
                     f"attachment {attachment.id}")

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

    def _handle_llm_error(self, exc: Exception) -> None:
        """
        Handle LLM processing errors by updating email status.
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


# Create LLMOCRTask instance for Celery task registration
llm_ocr_task_instance = LLMOCRTask()


@shared_task
def llm_ocr_task(
    email_id: str, force: bool = False, *args, **kwargs
) -> str:
    """
    Celery task for processing OCR content using LLM.

    This is a compatibility wrapper around the LLMOCRTask class.

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
    return llm_ocr_task_instance.run(email_id, force)
