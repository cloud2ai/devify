"""
Threadline Workflow CLI - Simple email processing workflow test.
"""
import logging
import time
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from threadline.models import EmailMessage
from threadline.tasks import process_email_chain

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Simple Threadline workflow test - process a single email through the complete pipeline.
    """
    help = 'Test complete email processing workflow for a single email'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email-id',
            type=int,
            required=True,
            help='Email ID to process through the complete workflow'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force reprocessing, ignore current status'
        )

    def handle(self, *args, **options):
        """
        Process a single email through the complete workflow.
        """
        email_id = options['email_id']
        force = options['force']

        logger.info(f"=== Starting email processing workflow ===")
        logger.info(f"Email ID: {email_id}")
        logger.info(f"Force mode: {force}")

        try:
            # Check if email exists
            try:
                email = EmailMessage.objects.get(id=email_id)
                logger.info(f"Found email: {email.subject}")
                logger.info(f"Current status: {email.status}")
                logger.info(f"User: {email.user.username}")
            except EmailMessage.DoesNotExist:
                logger.error(f"Email with ID {email_id} does not exist")
                return

            # Start the complete workflow
            logger.info("Starting complete email processing workflow...")
            start_time = time.time()

            # Run the workflow asynchronously
            # Note: process_email_chain creates an async chain and returns immediately
            result = process_email_chain.run(email_id, force)
            logger.info(f"Processing chain started successfully: {result}")

            end_time = time.time()
            duration = end_time - start_time

            logger.info(f"=== Workflow started successfully ===")
            logger.info(f"Duration: {duration:.2f} seconds")
            logger.info(f"Chain ID: {result}")

            # Show current email status
            email.refresh_from_db()
            logger.info(f"Current email status: {email.status}")
            logger.info("Processing chain is running in the background")

        except Exception as e:
            logger.error(f"Workflow failed: {e}")
            raise
