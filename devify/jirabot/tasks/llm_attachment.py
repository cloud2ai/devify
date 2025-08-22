"""
LLM Attachment Task using Celery Task class approach.

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
from jirabot.state_machine import AttachmentStatus, EmailStatus

logger = logging.getLogger(__name__)


class AttachmentOCRTask(Task):
    """
    LLM Attachment OCR organization task using Celery Task class.

    This class provides a unified execution flow for attachment processing
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
        self.task_name = "AttachmentsOCR"
        self.allowed_statuses = [
            EmailStatus.OCR_SUCCESS.value,
            EmailStatus.SUMMARY_FAILED.value
        ]

        # Get email object
        try:
            self.email = EmailMessage.objects.select_related(
                'user'
            ).get(
                id=email_id
            )
            logger.info(f"[AttachmentsOCR] Email object retrieved: {email_id}")
        except EmailMessage.DoesNotExist:
            logger.error(f"[AttachmentsOCR] EmailMessage {email_id} not found")
            raise

        logger.info(f"[AttachmentsOCR] Initialization completed "
                    f"for {email_id}, force: {force}")

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

            logger.info(f"[AttachmentsOCR] Start processing: {email_id}, "
                        f"force: {force}")

            # Step 1: Pre-execution check (status machine + force parameter)
            if not self._pre_execution_check():
                logger.info(f"[AttachmentsOCR] Pre-execution check failed, "
                            f"skipping to next task: {email_id}")
                return email_id

            # Step 2: Check if already complete
            if self._is_already_complete():
                return email_id

            # Step 3: Set processing status
            self._set_processing_status()

            # Step 4: Get attachments to process based on force parameter
            if not self.force:
                # Normal mode: only process attachments in OCR_SUCCESS state
                image_attachments = self.email.attachments.filter(
                    is_image=True,
                    status=AttachmentStatus.OCR_SUCCESS.value
                )
            else:
                # Force mode: process all image attachments
                image_attachments = self.email.attachments.filter(
                    is_image=True
                )

            # Step 5: Execute core business logic and complete task
            processing_results = self._execute_attachment_processing(
                image_attachments
            )

            logger.info(f"[AttachmentsOCR] Attachment processing task "
                        f"completed: {email_id}")
            return email_id

        except EmailMessage.DoesNotExist:
            logger.error(f"[AttachmentsOCR] EmailMessage {email_id} not found")
            raise
        except Exception as exc:
            logger.error(f"[AttachmentsOCR] Fatal error for {email_id}: {exc}")
            # Save error status to email (force mode handling is inside
            # _save_email)
            self._save_email(EmailStatus.SUMMARY_FAILED.value, str(exc))
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
            logger.debug(f"[AttachmentsOCR] Force mode enabled for email "
                         f"{self.email.id}, skipping status check")
            return True

        if self.email.status not in self.allowed_statuses:
            logger.warning(
                f"Email {self.email.id} cannot be processed in status: "
                f"{self.email.status}. Allowed: {self.allowed_statuses}"
            )
            return False

        logger.debug(f"[AttachmentsOCR] Pre-execution check passed for email "
                     f"{self.email.id}")
        return True

    def _is_already_complete(self) -> bool:
        """
        Check if attachment processing is already complete.

        Returns:
            bool: True if already complete
        """
        if self.force:
            logger.debug(f"[AttachmentsOCR] Force mode enabled for email "
                         f"{self.email.id}, skipping completion check")
            return False

        image_attachments = self.email.attachments.filter(is_image=True)

        # If no image attachments, return True
        if not image_attachments.exists():
            return True

        llm_success_count = image_attachments.filter(
            status=AttachmentStatus.LLM_SUCCESS.value
        ).count()

        if llm_success_count == image_attachments.count():
            logger.info(
                f"All image attachments for email {self.email.id} "
                f"already in LLM_SUCCESS state, skipping to next task"
            )
            return True

        return False

    def _set_processing_status(self) -> None:
        """
        Set the email to processing status.
        """
        if not self.force:
            # This task processes attachments for summary generation
            # So email status should be SUMMARY_PROCESSING
            self._save_email(EmailStatus.SUMMARY_PROCESSING.value)
        else:
            logger.info(f"[AttachmentsOCR] Force mode enabled - skipping "
                        "status checks for {self.email.id}")

    def _execute_attachment_processing(self, image_attachments) -> Dict:
        """
        Execute attachment processing for the email.

        Args:
            image_attachments: QuerySet of attachments to process
                              (already filtered based on force parameter)

        Returns:
            Dict: Attachment processing results
        """
        # Get prompt configuration
        prompt_config = Settings.get_user_prompt_config(
            self.email.user, ['ocr_prompt']
        )
        ocr_prompt = prompt_config['ocr_prompt']

        processed_count = 0
        skipped_count = 0

        for att in image_attachments:
            # Skip attachments with empty OCR content
            if not att.ocr_content or not att.ocr_content.strip():
                logger.warning(f"Attachment {att.id} ({att.filename}) has no "
                               "OCR content, skipping LLM organization")
                # Mark as LLM_SUCCESS since there's nothing to process
                self._save_attachment(att, AttachmentStatus.LLM_SUCCESS.value)
                skipped_count += 1
                continue

            try:
                # Call LLM to organize OCR content
                llm_result = call_llm(ocr_prompt, att.ocr_content)
                llm_content = llm_result.strip() if llm_result else ''

                # Determine status based on result
                if llm_content:
                    self._save_attachment(
                        att, AttachmentStatus.LLM_SUCCESS.value,
                        llm_content)
                    logger.info(f"LLM organization completed for "
                                f"attachment {att.id} "
                                f"({att.filename})")
                else:
                    # No content generated, still mark as success but
                    # log warning
                    self._save_attachment(
                        att, AttachmentStatus.LLM_SUCCESS.value)
                    logger.warning(f"LLM organization completed for "
                                   f"attachment {att.id} "
                                   f"({att.filename}) - no content generated")

                processed_count += 1

            except Exception as e:
                logger.error(f"LLM organization failed for attachment "
                             f"{att.id}: {e}")
                self._save_attachment(
                    att, AttachmentStatus.LLM_FAILED.value, '', str(e))
                # Don't increment processed_count for failed attachments

        # Handle non-image attachments that are still in FETCHED status
        non_image_attachments = self.email.attachments.filter(
            is_image=False,
            status=AttachmentStatus.FETCHED.value
        )
        for att in non_image_attachments:
            self._save_attachment(att, AttachmentStatus.LLM_SUCCESS.value)
            logger.info(f"Non-image attachment {att.id} "
                       f"({att.filename}) marked as LLM_SUCCESS")

        logger.info(f"[AttachmentsOCR] Attachments OCR organization completed: "
                   f"{processed_count} processed, {skipped_count} skipped "
                   f"(no OCR content)")

        return {
            'processed_count': processed_count,
            'skipped_count': skipped_count,
            'total_attachments': image_attachments.count()
        }

    def _save_attachment(
        self,
        attachment,
        status: str,
        llm_content: str = "",
        error_message: str = ""
    ) -> None:
        """
        Save attachment with status and content.
        In force mode, only save llm_content, skip status updates.

        Args:
            attachment: EmailAttachment object
            status: Status to set (only used in non-force mode)
            llm_content: LLM content to save
            error_message: Error message to set (only used in non-force mode)
        """
        # Always save llm_content (this is the main purpose of force mode)
        attachment.llm_content = llm_content

        if self.force:
            # Force mode: only save content, skip status updates
            attachment.save(update_fields=['llm_content'])
            logger.debug(f"[AttachmentsOCR] Force mode: saved content for "
                         f"attachment {attachment.id}")
        else:
            # Non-force mode: save everything
            attachment.status = status
            if error_message:
                attachment.error_message = error_message

            update_fields = ['status', 'llm_content']
            if error_message:
                update_fields.append('error_message')

            attachment.save(update_fields=update_fields)
            logger.debug(f"[AttachmentsOCR] Saved attachment {attachment.id} "
                         f"to {status}")

    def _save_email(self, status: str, error_message: str = "") -> None:
        """
        Save email with status and error message.
        In force mode, skip status updates.

        Args:
            status: Status to set (only used in non-force mode)
            error_message: Error message to set (only used in non-force mode)
        """
        if self.force:
            # Force mode: skip status updates
            logger.debug(f"[AttachmentsOCR] Force mode: skipping email status "
                         f"update to {status}")
            return

        # Non-force mode: save status
        self.email.status = status
        if error_message:
            self.email.error_message = error_message
        else:
            self.email.error_message = ""  # Clear any previous error

        update_fields = ['status', 'error_message']
        self.email.save(update_fields=update_fields)
        logger.debug(f"[AttachmentsOCR] Set email {self.email.id} to {status}")


# Create AttachmentOCRTask instance for Celery task registration
attachment_ocr_task = AttachmentOCRTask()


@shared_task(bind=True)
def organize_attachments_ocr_task(
    self, email_id: str, force: bool = False
) -> str:
    """
    Celery task for organizing attachments OCR content using LLM.

    This is a compatibility wrapper around the AttachmentOCRTask class.

    Args:
        email_id (str): ID of the email to process
        force (bool): Whether to force processing regardless of current status.
                     When True, skips status checks and allows reprocessing
                     even if the content already exists.

    Returns:
        str: The email_id for the next task in the chain
    """
    return attachment_ocr_task.run(email_id, force)
