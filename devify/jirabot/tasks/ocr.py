import logging
from celery import shared_task
from ..models import EmailMessage
from ..utils.ocr_handler import OCRHandler

logger = logging.getLogger(__name__)

@shared_task
def ocr_images_for_email(email_id):
    """
    Perform OCR on all image attachments of the given email.
    """
    try:
        email = EmailMessage.objects.get(id=email_id)
    except EmailMessage.DoesNotExist:
        logger.error(f"EmailMessage {email_id} does not exist")
        return

    # Set status to OCR_PROCESSING
    email.status = EmailMessage.ProcessingStatus.OCR_PROCESSING
    email.save(update_fields=['status'])

    # Check if there are any image attachments
    image_attachments = email.attachments.filter(is_image=True)
    if not image_attachments.exists():
        logger.info(f"No image attachments found for email {email_id}, "
                    f"skipping OCR and setting status to OCR_SUCCESS")
        email.status = EmailMessage.ProcessingStatus.OCR_SUCCESS
        email.error_message = ''  # Clear any previous error
        email.save(update_fields=['status', 'error_message'])
        return

    ocr_handler = OCRHandler()

    success_count = 0
    fail_count = 0
    failed_attachments = []

    for attachment in image_attachments:
        try:
            # Direct synchronous OCR recognize call
            text = ocr_handler.recognize(attachment.file_path)
            attachment.ocr_content = text
            attachment.save(update_fields=['ocr_content'])
            success_count += 1
        except Exception as e:
            logger.error(f"OCR failed for attachment {attachment.id}: {e}")
            fail_count += 1
            failed_attachments.append({
                'filename': attachment.filename,
                'error': str(e)
            })

    # Update email status
    if fail_count == 0 and success_count > 0:
        email.status = EmailMessage.ProcessingStatus.OCR_SUCCESS
        email.error_message = ''  # Clear any previous error
    elif fail_count > 0 and success_count == 0:
        failed_files = ', '.join([f"{item['filename']}({item['error']})"
                                 for item in failed_attachments])
        email.status = EmailMessage.ProcessingStatus.OCR_FAILED
        email.error_message = (
            f'OCR failed for all {fail_count} image attachments: {failed_files}'
        )
    elif fail_count > 0 and success_count > 0:
        failed_files = ', '.join([f"{item['filename']}({item['error']})"
                                 for item in failed_attachments])
        email.status = EmailMessage.ProcessingStatus.OCR_FAILED
        email.error_message = (
            f'OCR partially failed: {success_count} succeeded, '
            f'{fail_count} failed - Failed files: {failed_files}'
        )
    else:
        # This case should not happen since we check for image attachments above
        email.status = EmailMessage.ProcessingStatus.OCR_SUCCESS
        email.error_message = ''

    email.save(update_fields=['status', 'error_message'])