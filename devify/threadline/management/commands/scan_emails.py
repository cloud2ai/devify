"""
Management command for scanning emails for users.
"""

import logging
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.utils import timezone

from threadline.models import Settings, EmailTask
from threadline.tasks import scan_user_emails

# Initialize logger for this module
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Command to scan emails for all users or a specific user.
    """
    help = (
        'Scan emails for all users or a specific user'
    )

    def add_arguments(self, parser):
        """
        Add command line arguments for the management command.
        """
        parser.add_argument(
            '--user',
            type=str,
            help=(
                'Username to scan emails for (optional)'
            ),
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help=(
                'Force scan even if recent task exists'
            ),
        )
        parser.add_argument(
            '--debug',
            action='store_true',
            help=(
                'Enable debug logging for detailed output'
            ),
        )

    def handle(self, *args, **options):
        """
        Handle the command logic for scanning emails.
        """
        # Set debug logging level if debug flag is enabled
        if options['debug']:
            logging.getLogger().setLevel(logging.DEBUG)
            logger.info('Debug logging enabled')

        if options['user']:
            try:
                user = User.objects.get(
                    username=options['user']
                )
                self.scan_for_user(
                    user, options['force']
                )
            except User.DoesNotExist:
                logger.error(
                    f'User "{options["user"]}" does not exist'
                )
                raise CommandError(
                    f'User "{options["user"]}" does not exist'
                )
        else:
            users_with_settings = User.objects.filter(
                settings__key='email_config',
                settings__is_active=True
            ).distinct()

            if not users_with_settings.exists():
                logger.warning(
                    'No users with active email settings found'
                )
                return

            logger.info(
                f'Found {users_with_settings.count()} users with settings'
            )

            for user in users_with_settings:
                self.scan_for_user(
                    user, options['force']
                )

    def scan_for_user(self, user, force=False):
        """
        Scan emails for a specific user.
        """
        logger.info(
            f'Processing user: {user.username}'
        )

        # Check for recent task
        if not force:
            recent_task = (
                EmailTask.objects.filter(
                    user=user,
                    status__in=[
                        EmailTask.TaskStatus.PENDING,
                        EmailTask.TaskStatus.RUNNING
                    ],
                    created_at__gte=(
                        timezone.now() -
                        timedelta(minutes=5)
                    )
                ).first()
            )

            if recent_task:
                logger.warning(
                    f'User {user.username} has recent task '
                    f'(ID: {recent_task.id}), skipping'
                )
                return

        # Check if user has required settings
        try:
            email_config = user.settings.get(
                key='email_config', is_active=True
            )
            email_filter_config = user.settings.get(
                key='email_filter_config', is_active=True
            )
            logger.info(
                f'Found settings for user {user.username}'
            )
        except Settings.DoesNotExist as e:
            logger.error(
                f'Missing required settings for user '
                f'{user.username}: {e}'
            )
            return

        # Execute scan (sync call)
        try:
            scan_user_emails.run(user.id)
            logger.info(
                f'Successfully scanned emails for user {user.username}'
            )
        except Exception as e:
            logger.error(
                f'Failed to scan emails for user '
                f'{user.username}: {e}'
            )