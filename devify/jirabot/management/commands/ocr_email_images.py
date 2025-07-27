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

    def handle(self, *args, **options):
        email_id = options['email_id']
        try:
            email = EmailMessage.objects.get(id=email_id)
        except EmailMessage.DoesNotExist:
            logger.error(f"EmailMessage {email_id} does not exist")
            return

        ocr_images_for_email.run(email_id)
        logger.info(
            f"OCR task for EmailMessage {email_id} has been "
            f"dispatched to Celery."
        )