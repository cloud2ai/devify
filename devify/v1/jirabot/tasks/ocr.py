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

    ocr_handler = OCRHandler()

    success_count = 0
    fail_count = 0

    for attachment in email.attachments.filter(is_image=True):
        try:
            # Direct synchronous OCR recognize call
            text = ocr_handler.recognize(attachment.file_path)
            attachment.ocr_content = text
            attachment.save(update_fields=['ocr_content'])
            success_count += 1
        except Exception as e:
            logger.error(f"OCR failed for attachment {attachment.id}: {e}")
            fail_count += 1

    # Update email status
    if fail_count == 0 and success_count > 0:
        email.status = EmailMessage.ProcessingStatus.OCR_SUCCESS
    elif success_count == 0:
        email.status = EmailMessage.ProcessingStatus.OCR_FAILED
    else:
        email.status = EmailMessage.ProcessingStatus.OCR_FAILED
    email.save(update_fields=['status'])