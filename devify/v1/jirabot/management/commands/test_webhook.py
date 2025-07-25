import logging
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from v1.jirabot.models import EmailMessage, EmailTask
from v1.jirabot.tasks.notifications import (
    get_webhook_config,
    send_webhook_notification
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Test webhook configuration and send a test notification'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            required=True,
            help='Username to test webhook configuration for'
        )
        parser.add_argument(
            '--email-id',
            type=int,
            required=True,
            help='Email ID to use in test notification'
        )
        parser.add_argument(
            '--old-status',
            type=str,
            required=True,
            help='Old status for testing. Available values: pending, fetched, ocr_processing, ocr_failed, ocr_success, summary_processing, summary_failed, summary_success, jira_processing, jira_failed, jira_success, attachment_uploading, attachment_upload_failed, attachment_uploaded, success, failed, skipped'
        )
        parser.add_argument(
            '--new-status',
            type=str,
            required=True,
            help='New status for testing. Available values: pending, fetched, ocr_processing, ocr_failed, ocr_success, summary_processing, summary_failed, summary_success, jira_processing, jira_failed, jira_success, attachment_uploading, attachment_upload_failed, attachment_uploaded, success, failed, skipped'
        )

    def handle(self, *args, **options):
        """
        Test webhook configuration and send a test notification.
        """
        username = options['user']

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            logger.error(f'User "{username}" does not exist.')
            return

        # Get webhook configuration for this user
        config = get_webhook_config(user)

        logger.info("=== Webhook Configuration ===")
        if config:
            for key, value in config.items():
                logger.info(f"{key}: {value}")
        else:
            logger.warning("No valid webhook configuration found")

        # Check if webhook is properly configured
        if not config:
            logger.error("Webhook is not properly configured!")
            logger.warning(
                f"Please configure webhook settings for user '{username}' "
                f"in Django Admin Settings."
            )
            return

                                # Check if the specified email exists
        email_id = options['email_id']
        try:
            email = EmailMessage.objects.get(id=email_id, user=user)
            logger.info(f"Found email with ID: {email_id}")
            logger.info(f"Email subject: {email.subject}")
            logger.info(f"Email sender: {email.sender}")
            logger.info(f"Current email status: {email.status}")
        except EmailMessage.DoesNotExist:
            logger.error(f"Email with ID {email_id} does "
                         f"not exist for user {username}")
            return

        # Send test notification
        old_status = options['old_status']
        new_status = options['new_status']

        logger.info(f"=== Sending Test Notification ===")
        logger.info(f"User: {username}")
        logger.info(f"Email ID: {email_id}")
        logger.info(f"Status transition: {old_status} -> {new_status}")
        logger.info(f"Webhook URL: {config['url']}")

        try:
            # Send test notification synchronously for testing
            result = send_webhook_notification.run(
                email_id,
                old_status,
                new_status
            )

            logger.info("Test notification sent successfully!")

        except Exception as e:
            logger.error(f"Failed to send test notification: {e}")