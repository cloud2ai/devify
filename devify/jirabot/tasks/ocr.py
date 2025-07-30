import logging
from celery import shared_task
from ..models import EmailMessage
from ..utils.ocr_handler import OCRHandler

logger = logging.getLogger(__name__)

@shared_task
def ocr_images_for_email(email_id):
    """
    Perform OCR on all image attachments of the given email.
    Skip attachments that don't meet recognition conditions.
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
    skip_count = 0
    fail_count = 0
    failed_attachments = []
    skipped_attachments = []

    for attachment in image_attachments:
        try:
            # Direct synchronous OCR recognize call, ignore invalid images
            text = ocr_handler.recognize(attachment.file_path)

            # Check if OCR returned empty content (skipped by library)
            if not text or not text.strip():
                logger.info(f"OCR skipped attachment {attachment.id} "
                           f"({attachment.filename}) - no content recognized")
                attachment.ocr_content = ''
                attachment.save(update_fields=['ocr_content'])
                skip_count += 1
                skipped_attachments.append(attachment.filename)
            else:
                attachment.ocr_content = text
                attachment.save(update_fields=['ocr_content'])
                success_count += 1
                logger.info(f"OCR successful for attachment {attachment.id} "
                           f"({attachment.filename})")
        except Exception as e:
            logger.error(f"OCR failed for attachment {attachment.id}: {e}")
            fail_count += 1
            failed_attachments.append({
                'filename': attachment.filename,
                'error': str(e)
            })

    # Update email status based on results
    total_processed = success_count + skip_count + fail_count

    if fail_count == 0:
        # All attachments processed successfully (including skipped ones)
        email.status = EmailMessage.ProcessingStatus.OCR_SUCCESS
        email.error_message = ''  # Clear any previous error

        # Log summary of results
        if skip_count > 0:
            skipped_files = ', '.join(skipped_attachments)
            logger.info(f"OCR completed for email {email_id}: "
                       f"{success_count} successful, {skip_count} skipped "
                       f"(no content: {skipped_files})")
        else:
            logger.info(f"OCR completed for email {email_id}: "
                       f"{success_count} successful")
    else:
        # Some attachments failed
        failed_files = ', '.join([f"{item['filename']}({item['error']})"
                                 for item in failed_attachments])
        email.status = EmailMessage.ProcessingStatus.OCR_FAILED
        email.error_message = (
            f'OCR failed for {fail_count} image attachments: {failed_files}'
        )
        logger.error(f"OCR failed for email {email_id}: {email.error_message}")

    email.save(update_fields=['status', 'error_message'])