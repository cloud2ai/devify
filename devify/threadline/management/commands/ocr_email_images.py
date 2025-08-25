import logging
from django.core.management.base import BaseCommand
from ...models import EmailMessage
from ...tasks import ocr_images_for_email

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Perform OCR on all image attachments of the given email."

    def add_arguments(self, parser):
        parser.add_argument(
            '--email-id',
            type=int,
            required=True,
            help='ID of the EmailMessage to OCR'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force processing regardless of current status'
        )

    def handle(self, *args, **options):
        email_id = options['email_id']
        force = options['force']

        try:
            email = EmailMessage.objects.get(id=email_id)
        except EmailMessage.DoesNotExist:
            logger.error(f"EmailMessage {email_id} does not exist")
            return

        try:
            # Use synchronous execution for command line
            result = ocr_images_for_email.run(email_id, force=force)
            logger.info(
                f"OCR task for EmailMessage {email_id} has been "
                f"completed successfully."
            )
        except Exception as e:
            logger.error(f"Error executing OCR task: {e}")
            raise