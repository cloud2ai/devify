"""
OCR Task using Celery Task class approach.

ARCHITECTURE DESIGN
==================

Class Structure Overview
-----------------------
This OCRTask class follows a clean, layered architecture design that separates
concerns and makes the code easy to understand and maintain. It implements
the first stage of the email processing pipeline with proper state machine
integration.

Method Responsibilities
----------------------

1. before_start() - Initialization Layer
   Purpose: Handle all initialization work before task execution
   Responsibilities:
     - Set instance attributes (email_id, force, email, task_name)
     - Retrieve EmailMessage object from database
     - Initialize status machine constants (allowed_statuses, next_status)
     - Cache current email status for consistent use throughout task
   Design Principle: All setup work is done here, keeping the main logic clean

2. run() - Main Business Logic Controller
   Purpose: Orchestrate the entire task execution flow with state validation
   Responsibilities:
     - Control the execution sequence (pre-check -> process -> update)
     - Handle force parameter logic (centralized force handling)
     - Coordinate between different processing stages
     - Manage error handling and status updates
     - Ensure proper state machine transitions
   Design Principle: This is the only place where force logic is handled;
     lower-level methods don't need to know about force parameter

3. Helper Methods - Specialized Logic Handlers
   _pre_execution_check(): Status machine validation (FETCHED/OCR_FAILED only)
   _is_already_complete(): Check if already in OCR_SUCCESS state
   _set_processing_status(): Transition to OCR_PROCESSING state
   _execute_ocr_processing(): Core OCR business logic for image attachments
   _update_email_status(): Transition to OCR_SUCCESS/OCR_FAILED based on results
   _save_email(): Utility method for saving email with status and error
   _save_attachment(): Utility method for saving attachment OCR content
   _handle_ocr_error(): Error handling with OCR_FAILED status transition

State Machine Integration
------------------------

Allowed Input States:
  - FETCHED: Initial state after email fetch
  - OCR_FAILED: Previous OCR attempt failed, allows retry

Status Transitions:
  - FETCHED/OCR_FAILED → OCR_PROCESSING → OCR_SUCCESS (normal flow)
  - FETCHED/OCR_FAILED → OCR_PROCESSING → OCR_FAILED (error flow)

Force Mode Behavior:
  - Bypasses all status checks and validations
  - Skips status updates to prevent state machine corruption
  - Allows reprocessing regardless of current state
  - Used for manual reprocessing and debugging

Force Parameter Design Philosophy
--------------------------------

Centralized Force Logic
  Location: All force logic is handled in the run() method
  Benefit: Lower-level methods can focus purely on their business logic
  Implementation:
    - Status check bypassing when force=True
    - Status update skipping when force=True
    - Error handling bypass when force=True
    - Attachment reprocessing when force=True

Why This Design?
  1. Cleaner Code: Helper methods don't need to check force parameter
  2. Single Responsibility: Each method has one clear purpose
  3. Easier Testing: Can test business logic without force parameter complexity
  4. Better Maintainability: Force logic changes only need to be made in one
                             place
  5. State Machine Safety: Prevents force mode from corrupting workflow states

Data Flow
---------
1. Initialization (before_start) -> Set up task environment and status cache
2. Pre-execution Check -> Validate current status against allowed states
3. Completion Check -> Skip if already in OCR_SUCCESS state
4. Status Setting -> Transition to OCR_PROCESSING (normal mode only)
5. Attachment Processing -> Execute OCR on image attachments
6. Status Updates -> Transition to success/failed states (normal mode only)
7. Error Handling -> Handle failures with proper status transitions

Processing Logic
---------------
- Processes only image attachments (is_image=True)
- Skips attachments that already have OCR content (unless force=True)
- Saves empty string for failed OCR attempts
- Handles non-image attachments by skipping OCR processing
- Calculates success/failure statistics for status determination

Potential Issues and Mitigations
-------------------------------

State Machine Loop Risk:
  - OCR_FAILED can transition back to OCR_PROCESSING indefinitely
  - Current mitigation: Scheduler resets stuck tasks after 30 minutes
  - Recommended: Add retry count limits to prevent infinite loops

Error Scenarios:
  - OCR service unavailable: Results in OCR_FAILED status
  - Invalid image format: Saves empty OCR content, marks as success
  - File access issues: Results in OCR_FAILED status
  - Missing attachments: Marks email as OCR_SUCCESS

Recovery Mechanisms:
  - Automatic retry through OCR_FAILED → OCR_PROCESSING transition
  - Scheduler timeout reset for stuck processing states
  - Force mode for manual intervention and debugging

Benefits of This Architecture
----------------------------
- Separation of Concerns: Each method has a single, clear responsibility
- Force Logic Isolation: Force parameter handling is centralized and
                         predictable
- State Machine Compliance: Proper integration with email workflow states
- Testability: Each layer can be tested independently
- Maintainability: Changes to force logic or business logic are isolated
- Readability: The main flow in run() method is easy to follow
- Reusability: Helper methods can be reused or modified without affecting
               force logic

This design pattern can be applied to other Celery tasks that need similar
force parameter handling and clean separation of concerns while maintaining
proper state machine integration.
"""


# Import statements
from celery import Task, shared_task
import logging
from typing import Dict, Any

from threadline.models import EmailMessage
from threadline.utils.ocr_handler import OCRHandler
from threadline.state_machine import EmailStatus

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

        # For EmailMessage Status Control
        self.allowed_statuses = [
            EmailStatus.FETCHED.value,
            EmailStatus.OCR_FAILED.value
        ]
        self.next_success_status = EmailStatus.OCR_SUCCESS.value
        self.processing_status = EmailStatus.OCR_PROCESSING.value
        self.next_failed_status = EmailStatus.OCR_FAILED.value

        # Get email object
        try:
            self.email = EmailMessage.objects.select_related('user').get(
                id=email_id)

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

            # Step 3: Set processing status (skip in force mode)
            if not self.force:
                logger.info(f"[{self.task_name}] Setting processing "
                            f"status for email {email_id}")
                self._set_processing_status()

            # Step 4: Process attachments (always execute, pass
            # force_mode parameter)
            image_attachments = self.email.attachments.filter(is_image=True)
            logger.info(f"[{self.task_name}] Processing "
                        f"{image_attachments.count()} image attachments, "
                        f"force: {self.force}")
            ocr_results = self._execute_ocr_processing(
                image_attachments, force_mode=self.force)

            # Step 5: Update email status (skip in force mode)
            if not self.force:
                logger.info(f"[{self.task_name}] Updating email "
                            f"status for email {email_id}")
                self._update_email_status(ocr_results)
            else:
                logger.info(f"[{self.task_name}] Force mode: skipping "
                            f"status updates for {email_id}")

            logger.info(f"[{self.task_name}] OCR processing completed: "
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
                self._handle_ocr_error(exc)
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
        Check if OCR is already complete.

        Returns:
            bool: True if already complete
        """
        if self.current_status == self.next_success_status:
            logger.info(
                f"[{self.task_name}] Email {self.email_id} already in "
                f"{self.next_success_status} state, "
                f"skipping to next task"
            )
            return True

        return False

    def _set_processing_status(self) -> None:
        """
        Set email to processing status.
        """
        self._save_email(status=self.processing_status)

    def _execute_ocr_processing(
        self,
        image_attachments,
        force_mode: bool = False
    ) -> Dict:
        """
        Execute OCR processing for image attachments.

        Args:
            image_attachments: QuerySet of image attachments to process
            force_mode: If True, reprocess all attachments; if False, skip
                        existing content

        Returns:
            Dict: OCR processing results
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

        # Process image attachments
        ocr_handler = OCRHandler()
        attachment_results = []  # Store results for each attachment

        for attachment in image_attachments:
            # Check if we should skip this attachment based on mode
            if not force_mode and attachment.ocr_content:
                logger.info(f"[{self.task_name}] Attachment "
                            f"{attachment.id} ({attachment.filename}) already "
                            f"has OCR content, skipping in normal mode")
                attachment_results.append({
                    'id': attachment.id,
                    'success': True,
                    'skipped': True,
                    'reason': 'Already has OCR content'
                })
                continue

            try:
                # Perform OCR (either because force=True or no existing content)
                logger.info(f"[{self.task_name}] Processing attachment "
                            f"{attachment.id} ({attachment.file_path}) - "
                            f"no existing content")

                text = ocr_handler.recognize(attachment.file_path)

                # Save OCR result
                if text and text.strip():
                    logger.info(f"OCR successful for attachment "
                               f"{attachment.id} ({attachment.file_path})")
                    self._save_attachment(attachment, text.strip())
                    attachment_results.append({
                        'id': attachment.id,
                        'success': True,
                        'skipped': False
                    })
                else:
                    logger.warning(f"OCR completed for attachment "
                                   f"{attachment.id} ({attachment.filename}) "
                                   f"- no content recognized")
                    self._save_attachment(attachment, '')
                    attachment_results.append({
                        'id': attachment.id,
                        'success': True,
                        'skipped': False
                    })

            except Exception as e:
                logger.error(f"OCR failed for attachment "
                             f"{attachment.id}: {e}")
                # Save empty OCR content for failed attachment
                self._save_attachment(attachment, '')
                attachment_results.append({
                    'id': attachment.id,
                    'success': False,
                    'error': str(e),
                    'skipped': False
                })

        # Handle non-image attachments - skip OCR processing
        non_image_attachments = self.email.attachments.filter(
            is_image=False
        )
        for attachment in non_image_attachments:
            # No OCR content to save for non-image attachments
            logger.info(f"[{self.task_name}] Non-image attachment "
                       f"{attachment.id} ({attachment.filename}) skipped "
                       f"OCR processing")

        # Calculate statistics
        # Calculate the number of successful and not skipped attachments
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

    def _update_email_status(self, ocr_results: Dict) -> None:
        """
        Update email status based on OCR results.
        This is called after all attachments have been processed.

        Args:
            ocr_results: Results from OCR processing
        """
        if ocr_results['no_attachments']:
            # No image attachments to process
            self._save_email(status=self.next_success_status)
            return

        if ocr_results['fail_count'] == 0:
            # All attachments processed successfully (including skipped ones)
            self._save_email(status=self.next_success_status)

            # Log detailed results
            if ocr_results.get('skipped_count', 0) > 0:
                logger.info(
                    f"[{self.task_name}] OCR completed for email "
                    f"{self.email_id}: "
                    f"{ocr_results['success_count']} processed, "
                    f"{ocr_results['skipped_count']} skipped "
                    f"(already had content)"
                )
            else:
                logger.info(f"[{self.task_name}] OCR completed for "
                            f"email {self.email_id}: "
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
                status=self.next_failed_status,
                error_message=error_message
            )
            logger.error(f"[{self.task_name}] OCR failed for email "
                         f"{self.email_id}: {error_message}")

    def _save_attachment(self, attachment, ocr_content: str = "") -> None:
        """
        Save attachment with OCR content.
        This method is pure - only saves attachment content, no status logic.

        Args:
            attachment: EmailAttachment object to save
            ocr_content: OCR content to save
        """
        attachment.ocr_content = ocr_content
        attachment.save(update_fields=['ocr_content'])
        logger.debug(f"[{self.task_name}] Saved OCR content for "
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

    def _handle_ocr_error(self, exc: Exception) -> None:
        """
        Handle OCR processing errors by updating email status.
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


# Create OCRTask instance for Celery task registration
ocr_task = OCRTask()


@shared_task
def ocr_images_for_email(
    email_id: str,
    force: bool = False,
    *args,
    **kwargs
) -> str:
    """
    Celery task for performing OCR on all image attachments of an email.

    This is a compatibility wrapper around the OCRTask class.

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
    return ocr_task.run(email_id, force)
