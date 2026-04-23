import logging

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from threadline.models import EmailMessage
from threadline.services.workflow_config import (
    resolve_threadline_notification_channel,
)
from threadline.tasks.notifications import (
    build_email_failure_text,
    send_threadline_notification,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Test the configured Threadline notification channel by sending "
        "a synthetic failure notification"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--user",
            type=str,
            required=True,
            help="Username to test the notification channel for",
        )
        parser.add_argument(
            "--email-id",
            type=int,
            required=True,
            help="Email ID to use in the test notification",
        )
        parser.add_argument(
            "--status",
            type=str,
            required=True,
            help=(
                "Simulated status for the test payload. The command sends a "
                "failure notification through the configured channel."
            ),
        )

    def handle(self, *args, **options):
        username = options["user"]

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            logger.error(f'User "{username}" does not exist.')
            return

        channel = resolve_threadline_notification_channel()
        if channel:
            logger.info("=== Threadline Notification Channel ===")
            logger.info(f"uuid: {channel.uuid}")
            logger.info(f"type: {channel.channel_type}")
            logger.info(f"name: {channel.name}")
        else:
            logger.warning(
                "No configured Threadline notification channel found"
            )

        email_id = options["email_id"]
        try:
            email = EmailMessage.objects.get(id=email_id, user=user)
            logger.info(f"Found email with ID: {email_id}")
            logger.info(f"Email subject: {email.subject}")
            logger.info(f"Email sender: {email.sender}")
            logger.info(f"Current email status: {email.status}")
        except EmailMessage.DoesNotExist:
            logger.error(
                f"Email with ID {email_id} does not exist for user "
                f"{username}"
            )
            return

        simulated_status = options["status"]
        language = (channel.config or {}).get("language") if channel else None
        logger.info("=== Sending Test Notification ===")
        logger.info(f"User: {username}")
        logger.info(f"Email ID: {email_id}")
        logger.info(
            f"Simulated status transition: {email.status} -> "
            f"{simulated_status}"
        )

        try:
            failure_text = build_email_failure_text(
                email,
                email.status,
                simulated_status,
                language=language,
            )
            result = send_threadline_notification.run(
                failure_text,
                "manual_test",
                f"email:{email.id}",
                user_id=user.id,
            )

            logger.info(f"Test notification sent successfully: {result}")
        except Exception as exc:
            logger.error(f"Failed to send test notification: {exc}")
