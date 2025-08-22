from celery import shared_task
import logging

from django.core.exceptions import ValidationError

from jirabot.models import EmailMessage
from jirabot.utils.ocr_handler import OCRHandler
from jirabot.state_machine import AttachmentStatus, EmailStatus

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def ocr_images_for_email(
    self, email_id: str, force: bool = False
) -> str:
    """
    Celery task for performing OCR on all image attachments of an email.

    Args:
        email_id (str): ID of the email to process
        force (bool): Whether to force processing regardless of current status.
                     When True, skips status checks and allows reprocessing
                     even if the content already exists.

    Returns:
        str: The email_id for the next task in the chain
    """
    try:
        email = EmailMessage.objects.get(id=email_id)
        logger.info(
            f"[OCR] Start processing: {email_id}, force: {force}"
        )

        # Status check: Only enforce status restrictions in non-force mode
        # In force mode, we allow reprocessing regardless of current status
        if not force:
            allow_status = [
                EmailStatus.FETCHED.value,
                EmailStatus.OCR_FAILED.value
            ]
            if email.status not in allow_status:
                logger.warning(
                    f"Email {email_id} cannot be processed in "
                    f"status: {email.status}"
                )
                return email_id

            # Check if all image attachments are already in OCR_SUCCESS state
            # (only in non-force mode)
            image_attachments = email.attachments.filter(is_image=True)
            if image_attachments.exists():
                ocr_success_count = image_attachments.filter(
                    status=AttachmentStatus.OCR_SUCCESS.value
                ).count()

                if ocr_success_count == image_attachments.count():
                    logger.info(
                        f"All image attachments for email {email_id} already in "
                        f"OCR_SUCCESS state, skipping to next task"
                    )
                    # Set email status to OCR_SUCCESS if not already set
                    if email.status != EmailStatus.OCR_SUCCESS.value:
                        email.status = EmailStatus.OCR_SUCCESS.value
                        email.save(update_fields=['status'])
                    return email_id

            # Set status to OCR_PROCESSING (only in non-force mode)
            email.status = EmailStatus.OCR_PROCESSING.value
            email.save(update_fields=['status'])
        else:
            logger.info(
                f"[OCR] Force mode enabled - skipping status checks "
                f"for {email_id}"
            )

        # Execute OCR business logic
        ocr_results = _execute_ocr_processing(email, force)

        # Update statuses only in non-force mode
        if not force:
            _update_attachment_statuses(ocr_results)
            _update_email_status(email, ocr_results)

        logger.info(f"[OCR] OCR processing task completed: {email_id}")
        return email_id

    except EmailMessage.DoesNotExist:
        logger.error(f"[OCR] EmailMessage {email_id} not found")
        raise
    except Exception as exc:
        logger.error(f"[OCR] Fatal error for {email_id}: {exc}")
        if not force:
            _handle_ocr_error(email_id, exc)
        raise


def _execute_ocr_processing(email: EmailMessage, force: bool) -> dict:
    """
    Execute OCR business logic for all attachments.

    Args:
        email: EmailMessage instance
        force: Whether to force processing

    Returns:
        dict: OCR processing results
    """
    # Get image attachments that need OCR processing
    # In non-force mode: only process attachments in FETCHED or OCR_FAILED state
    # In force mode: process all image attachments regardless of state
    if not force:
        image_attachments = email.attachments.filter(
            is_image=True,
            status__in=[
                AttachmentStatus.FETCHED.value,
                AttachmentStatus.OCR_FAILED.value
            ]
        )
    else:
        image_attachments = email.attachments.filter(is_image=True)

    if not image_attachments.exists():
        logger.info(f"No image attachments to process for email {email.id}, "
                    f"setting email status to OCR_SUCCESS")
        return {
            'success_count': 0,
            'fail_count': 0,
            'failed_attachments': [],
            'no_attachments': True
        }

    ocr_handler = OCRHandler()
    success_count = 0
    fail_count = 0
    failed_attachments = []

    for attachment in image_attachments:
        try:
            # Direct synchronous OCR recognize call, ignore invalid images
            text = ocr_handler.recognize(attachment.file_path)

            # Save OCR result (even if empty)
            attachment.ocr_content = text.strip() if text else ''
            attachment.save(update_fields=['ocr_content'])

            if text and text.strip():
                logger.info(f"OCR successful for attachment "
                           f"{attachment.id} ({attachment.filename})")
            else:
                # No content recognized, still mark as success but log warning
                logger.warning(f"OCR completed for attachment "
                               f"{attachment.id} ({attachment.filename}) - "
                               f"no content recognized")
            success_count += 1

        except Exception as e:
            logger.error(f"OCR failed for attachment {attachment.id}: {e}")
            attachment.error_message = str(e)
            attachment.save(update_fields=['error_message'])
            fail_count += 1
            failed_attachments.append({
                'filename': attachment.filename,
                'error': str(e)
            })

    # Handle non-image attachments - mark them as LLM_SUCCESS (skip OCR)
    non_image_attachments = email.attachments.filter(
        is_image=False,
        status=AttachmentStatus.FETCHED.value
    )
    for attachment in non_image_attachments:
        attachment.status = AttachmentStatus.LLM_SUCCESS.value
        attachment.save(update_fields=['status'])
        logger.info(f"Non-image attachment {attachment.id} "
                   f"({attachment.filename}) marked as LLM_SUCCESS")

    return {
        'success_count': success_count,
        'fail_count': fail_count,
        'failed_attachments': failed_attachments,
        'no_attachments': False
    }


def _update_attachment_statuses(ocr_results: dict):
    """
    Update attachment statuses based on OCR results.

    Args:
        ocr_results: Results from OCR processing
    """
    # Note: Attachment statuses are updated during OCR processing
    # This function is kept for future extensibility if needed
    # Currently, attachment statuses are updated in _execute_ocr_processing
    # to avoid state machine validation conflicts
    pass


def _update_email_status(email: EmailMessage, ocr_results: dict):
    """
    Update email status based on OCR results.

    Args:
        email: EmailMessage instance
        ocr_results: Results from OCR processing
    """
    if ocr_results['no_attachments']:
        # No image attachments to process
        email.status = EmailStatus.OCR_SUCCESS.value
        email.error_message = ''  # Clear any previous error
        email.save(update_fields=['status', 'error_message'])
        return

    if ocr_results['fail_count'] == 0:
        # All attachments processed successfully
        email.status = EmailStatus.OCR_SUCCESS.value
        email.error_message = ''  # Clear any previous error
        logger.info(f"[OCR] OCR completed for email {email.id}: "
                   f"{ocr_results['success_count']} successful")
    else:
        # Some attachments failed
        failed_files = ', '.join([f"{item['filename']}({item['error']})"
                                 for item in ocr_results['failed_attachments']])
        email.status = EmailStatus.OCR_FAILED.value
        email.error_message = (
            f'OCR failed for {ocr_results["fail_count"]} image attachments: {failed_files}'
        )
        logger.error(f"[OCR] OCR failed for email {email.id}: "
                     f"{email.error_message}")

    email.save(update_fields=['status', 'error_message'])


def _handle_ocr_error(email_id: str, exc: Exception):
    """
    Handle OCR processing errors by updating email status.

    Args:
        email_id: ID of the email
        exc: Exception that occurred
    """
    try:
        email = EmailMessage.objects.get(id=email_id)
        email.status = EmailStatus.OCR_FAILED.value
        email.error_message = str(exc)
        email.save(update_fields=['status', 'error_message'])
    except Exception:
        logger.error(f"[OCR] Failed to set status for {email_id}")
