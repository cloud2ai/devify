"""
OCR Task using Celery Task class approach.

ARCHITECTURE DESIGN
==================

Class Structure Overview
-----------------------
This OCRTask class follows a clean, layered architecture design that separates
concerns and makes the code easy to understand and maintain.

Method Responsibilities
----------------------

1. before_start() - Initialization Layer
   Purpose: Handle all initialization work before task execution
   Responsibilities:
     - Set instance attributes (email_id, force, email, task_name,
                                allowed_statuses)
     - Retrieve EmailMessage object from database
     - Initialize task-specific constants and configurations
   Design Principle: All setup work is done here, keeping the main logic clean

2. run() - Main Business Logic Controller
   Purpose: Orchestrate the entire task execution flow
   Responsibilities:
     - Control the execution sequence (pre-check -> process -> update)
     - Handle force parameter logic (centralized force handling)
     - Coordinate between different processing stages
     - Manage error handling and status updates
   Design Principle: This is the only place where force logic is handled;
     lower-level methods don't need to know about force parameter

3. Helper Methods - Specialized Logic Handlers
   _pre_execution_check(): Status machine validation + force parameter logic
   _is_already_complete(): Check if task is already completed
   _set_processing_status(): Set email to processing state
   _execute_ocr_processing(): Core OCR business logic (pure processing, no
                              force logic)
   _update_attachment_statuses(): Update attachment statuses based on results
   _update_email_status(): Update email status based on processing results
   _save_email(): Utility method for saving email with status and error
   _save_attachment(): Utility method for saving attachment with status and
                       content
   _handle_ocr_error(): Error handling and status updates

Force Parameter Design Philosophy
--------------------------------

Centralized Force Logic
  Location: All force logic is handled in the run() method
  Benefit: Lower-level methods can focus purely on their business logic
  Implementation:
    - Attachment selection based on force parameter
    - Status update skipping when force is enabled
    - Error handling bypass when force is enabled

Why This Design?
  1. Cleaner Code: Helper methods don't need to check force parameter
  2. Single Responsibility: Each method has one clear purpose
  3. Easier Testing: Can test business logic without force parameter complexity
  4. Better Maintainability: Force logic changes only need to be made in one
                             place

Data Flow
---------
1. Initialization (before_start) -> Set up task environment
2. Pre-execution Check -> Validate if task should run
3. Completion Check -> Skip if already done
4. Status Setting -> Mark as processing
5. Attachment Selection -> Choose attachments based on force parameter
6. Core Processing -> Execute OCR logic (pure business logic)
7. Status Updates -> Update results (skipped if force mode)
8. Error Handling -> Handle failures (skipped if force mode)

Benefits of This Architecture
----------------------------
- Separation of Concerns: Each method has a single, clear responsibility
- Force Logic Isolation: Force parameter handling is centralized and
                         predictable
- Testability: Each layer can be tested independently
- Maintainability: Changes to force logic or business logic are isolated
- Readability: The main flow in run() method is easy to follow
- Reusability: Helper methods can be reused or modified without affecting
               force logic

This design pattern can be applied to other Celery tasks that need similar
force parameter handling and clean separation of concerns.
"""


# Import statements
from celery import Task, shared_task
import logging
from typing import Dict, Any

from threadline.models import EmailMessage
from threadline.utils.ocr_handler import OCRHandler
from threadline.state_machine import AttachmentStatus, EmailStatus

logger = logging.getLogger(__name__)


class OCRTask(Task):
    """
    OCR processing task using Celery Task class.

    This class provides a unified execution flow for OCR processing
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
        self.task_name = "OCR"
        self.allowed_statuses = [
            EmailStatus.FETCHED.value,
            EmailStatus.OCR_FAILED.value
        ]

        # Get email object
        try:
            self.email = EmailMessage.objects.select_related('user').get(
                id=email_id)
            logger.info(f"[OCR] Email object retrieved: {email_id}")
        except EmailMessage.DoesNotExist:
            logger.error(f"[OCR] EmailMessage {email_id} not found")
            raise

        logger.info(f"[OCR] Initialization completed for {email_id}, "
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

            logger.info(f"[OCR] Start processing: {email_id}, force: {force}")

            # Step 1: Pre-execution check (status machine + force parameter)
            if not self._pre_execution_check():
                logger.info(f"[OCR] Pre-execution check failed, skipping to "
                            f"next task: {email_id}")
                return email_id

            # Step 2: Check if already complete
            if self._is_already_complete():
                return email_id

            # Step 3: Set processing status
            self._set_processing_status()

            # Step 4: Get image attachments based on force parameter
            if self.force:
                image_attachments = self.email.attachments.filter(
                    is_image=True)
            else:
                image_attachments = self.email.attachments.filter(
                    is_image=True,
                    status__in=[
                        AttachmentStatus.FETCHED.value,
                        AttachmentStatus.OCR_FAILED.value
                    ]
                )
            ocr_results = self._execute_ocr_processing(image_attachments)

            # Step 5: Update statuses based on result
            if self.force:
                logger.warning(f"[OCR] Force mode enabled - skipping status "
                               f"updates for {email_id}")
            else:
                self._update_attachment_statuses(ocr_results)
                self._update_email_status(ocr_results)

            logger.info(f"[OCR] OCR processing task completed: {email_id}")
            return email_id

        except EmailMessage.DoesNotExist:
            logger.error(f"[OCR] EmailMessage {email_id} not found")
            raise
        except Exception as exc:
            logger.error(f"[OCR] Fatal error for {email_id}: {exc}")
            if self.force:
                logger.warning(f"[OCR] Force mode enabled - skipping error "
                               f"handling for {email_id}")
            else:
                self._handle_ocr_error(exc)
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
            logger.debug(f"[OCR] Force mode enabled for email "
                         f"{self.email.id}, skipping status check")
            return True

        if self.email.status not in self.allowed_statuses:
            logger.warning(
                f"Email {self.email.id} cannot be processed in status: "
                f"{self.email.status}. Allowed: {self.allowed_statuses}"
            )
            return False

        logger.debug(f"[OCR] Pre-execution check passed for email "
                     f"{self.email.id}")
        return True

    def _is_already_complete(self) -> bool:
        """
        Check if OCR processing is already complete.

        Returns:
            bool: True if already complete
        """
        if self.force:
            logger.debug(f"[OCR] Force mode enabled for email "
                         f"{self.email.id}, skipping completion check")
            return False

        image_attachments = self.email.attachments.filter(is_image=True)
        if not image_attachments.exists():
            return True

        ocr_success_count = image_attachments.filter(
            status=AttachmentStatus.OCR_SUCCESS.value
        ).count()

        if ocr_success_count == image_attachments.count():
            logger.info(
                f"All image attachments for email {self.email.id} already in "
                f"OCR_SUCCESS state, skipping to next task"
            )
            # Set email status to OCR_SUCCESS if not already set
            if self.email.status != EmailStatus.OCR_SUCCESS.value:
                self._save_email(EmailStatus.OCR_SUCCESS.value)
            return True

        return False

    def _set_processing_status(self) -> None:
        """
        Set the email to processing status.
        """
        if not self.force:
            self._save_email(EmailStatus.OCR_PROCESSING.value)
        else:
            logger.info(f"[OCR] Force mode enabled - skipping status checks "
                        f"for {self.email.id}")

    def _execute_ocr_processing(self, image_attachments) -> Dict:
        """
        Execute OCR processing for the provided image attachments.

        Args:
            image_attachments: QuerySet of image attachments to process

        Returns:
            Dict: OCR processing results
        """
        if not image_attachments.exists():
            logger.info(f"No image attachments to process for "
                        f"email {self.email.id}")
            return {
                'attachment_results': [],
                'success_count': 0,
                'fail_count': 0,
                'no_attachments': True
            }

        # Process image attachments
        ocr_handler = OCRHandler()
        attachment_results = []  # Store results for each attachment

        for attachment in image_attachments:
            try:
                # Set attachment to processing status first (required by state machine)
                self._save_attachment(
                    attachment,
                    AttachmentStatus.OCR_PROCESSING.value
                )

                # Perform OCR
                text = ocr_handler.recognize(attachment.file_path)

                # Save OCR result and update status
                if text and text.strip():
                    logger.info(f"OCR successful for attachment "
                               f"{attachment.id} ({attachment.filename})")
                    self._save_attachment(
                        attachment,
                        AttachmentStatus.OCR_SUCCESS.value,
                        ocr_content=text.strip()
                    )
                    attachment_results.append({
                        'id': attachment.id,
                        'status': AttachmentStatus.OCR_SUCCESS.value,
                        'success': True
                    })
                else:
                    logger.warning(f"OCR completed for attachment "
                                   f"{attachment.id} ({attachment.filename}) "
                                   f"- no content recognized")
                    self._save_attachment(
                        attachment,
                        AttachmentStatus.OCR_SUCCESS.value,
                        ocr_content=''
                    )
                    attachment_results.append({
                        'id': attachment.id,
                        'status': AttachmentStatus.OCR_SUCCESS.value,
                        'success': True
                    })

            except Exception as e:
                logger.error(f"OCR failed for attachment {attachment.id}: {e}")
                self._save_attachment(
                    attachment,
                    AttachmentStatus.OCR_FAILED.value,
                    error_message=str(e)
                )
                attachment_results.append({
                    'id': attachment.id,
                    'status': AttachmentStatus.OCR_FAILED.value,
                    'success': False,
                    'error': str(e)
                })

        # Handle non-image attachments - mark them as LLM_SUCCESS (skip OCR)
        non_image_attachments = self.email.attachments.filter(
            is_image=False,
            status=AttachmentStatus.FETCHED.value
        )
        for attachment in non_image_attachments:
            self._save_attachment(
                attachment,
                AttachmentStatus.LLM_SUCCESS.value
            )
            logger.info(f"Non-image attachment {attachment.id} "
                       f"({attachment.filename}) marked as LLM_SUCCESS")

        # Note: Non-image attachments are not part of OCR processing
        # They will be handled by other tasks (e.g., LLM processing)
        success_count = len([r for r in attachment_results if r['success']])
        fail_count = len([r for r in attachment_results if not r['success']])
        return {
            'attachment_results': attachment_results,
            'success_count': success_count,
            'fail_count': fail_count,
            'no_attachments': False
        }

    def _update_attachment_statuses(self, ocr_results: Dict) -> None:
        """
        Update attachment statuses based on OCR results.

        This method ensures all attachment statuses are properly updated
        after OCR processing, including both successful and failed cases.

        Args:
            ocr_results: Results from OCR processing
        """
        if ocr_results['no_attachments']:
            return

        # Note: Attachment statuses are already updated during OCR processing
        # This method is kept for future extensibility if needed
        # Currently, attachment statuses are updated in _execute_ocr_processing
        # to avoid state machine validation conflicts
        logger.info(f"[OCR] Attachment statuses already updated during "
                    f"processing")

    def _update_email_status(self, ocr_results: Dict) -> None:
        """
        Update email status based on OCR results.

        Args:
            ocr_results: Results from OCR processing
        """
        if ocr_results['no_attachments']:
            # No image attachments to process
            self._save_email(EmailStatus.OCR_SUCCESS.value)
            return

        if ocr_results['fail_count'] == 0:
            # All attachments processed successfully
            self._save_email(EmailStatus.OCR_SUCCESS.value)
            logger.info(f"[OCR] OCR completed for email {self.email.id}: "
                        f"{ocr_results['success_count']} successful")
        else:
            # Some attachments failed
            # Collect all failed attachment results for error reporting
            failed_results = [
                result for result in ocr_results['attachment_results']
                if not result['success']
            ]
            failed_files = ', '.join([
                f"attachment_{item['id']}({item['error']})"
                for item in failed_results
            ])
            error_message = (
                f'OCR failed for {ocr_results["fail_count"]} image '
                f'attachments: {failed_files}'
            )

            self._save_email(
                EmailStatus.OCR_FAILED.value,
                error_message=error_message
            )
            logger.error(f"[OCR] OCR failed for email {self.email.id}: "
                         f"{error_message}")

    def _save_email(self, status: str = "", error_message: str = "") -> None:
        """
        Save email with status and error message.
        In force mode, skip status updates.

        Args:
            status: Status to set (only used in non-force mode)
            error_message: Error message to set (only used in non-force mode)
        """
        if self.force:
            # Force mode: skip status updates
            logger.debug(f"[OCR] Force mode: skipping email status update to "
                         f"{status}")
            return

        # Non-force mode: save status
        self.email.status = status
        if error_message:
            self.email.error_message = error_message
        else:
            self.email.error_message = ""  # Clear any previous error

        update_fields = ['status', 'error_message']
        self.email.save(update_fields=update_fields)
        logger.debug(f"[OCR] Saved email {self.email.id} to {status}")

    def _save_attachment(
        self,
        attachment,
        status: str,
        ocr_content: str = "",
        error_message: str = ""
    ) -> None:
        """
        Save attachment with status, OCR content, and optionally error message.
        In force mode, only save OCR content, skip status updates.

        Args:
            attachment: EmailAttachment object
            status: Status to set (only used in non-force mode)
            ocr_content: OCR content to save (always saved)
            error_message: Error message to set (only used in non-force mode)
        """
        # Always save OCR content (this is the main purpose of force mode)
        if ocr_content is not None:
            attachment.ocr_content = ocr_content

        if self.force:
            # Force mode: only save content, skip status updates
            if ocr_content is not None:
                attachment.save(update_fields=['ocr_content'])
                logger.debug(f"[OCR] Force mode: saved OCR content for "
                             f"attachment {attachment.id}")
            return

        # Non-force mode: save everything
        attachment.status = status
        if error_message:
            attachment.error_message = error_message
        else:
            attachment.error_message = ""  # Clear any previous error

        update_fields = ['status']
        if ocr_content is not None:
            update_fields.append('ocr_content')
        if error_message:
            update_fields.append('error_message')

        attachment.save(update_fields=update_fields)
        logger.debug(f"[OCR] Saved attachment {attachment.id} to {status}")

    def _handle_ocr_error(self, exc: Exception) -> None:
        """
        Handle OCR processing errors by updating email status.

        Args:
            exc: Exception that occurred
        """
        try:
            self._save_email(
                EmailStatus.OCR_FAILED.value,
                error_message=str(exc)
            )
        except Exception:
            logger.error(f"[OCR] Failed to set status for {self.email_id}")


# Create OCRTask instance for Celery task registration
ocr_task = OCRTask()


@shared_task(bind=True)
def ocr_images_for_email(self, email_id: str, force: bool = False) -> str:
    """
    Celery task for performing OCR on all image attachments of an email.

    This is a compatibility wrapper around the OCRTask class.

    Args:
        email_id (str): ID of the email to process
        force (bool): Whether to force processing regardless of current status.
                     When True, skips status checks and allows reprocessing
                     even if the content already exists.

    Returns:
        str: The email_id for the next task in the chain
    """
    return ocr_task.run(email_id, force)
