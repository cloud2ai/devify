"""
Management command for testing issue creation task.
"""

from django.core.management.base import BaseCommand
import logging

from threadline.tasks import create_issue_task

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    Command to test issue creation task.
    """
    help = (
        'Create issue from processed email for a given email_id. '
        'Use --force to reprocess even if already processed.'
    )

    def add_arguments(self, parser):
        """
        Add command line arguments for the management command.
        """
        parser.add_argument(
            '--email-id',
            type=int,
            required=True,
            help='Email message ID to create issue from (required)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force reprocess even if already processed'
        )

    def handle(self, *args, **options):
        """
        Handle the command logic for testing issue creation.
        """
        email_id = options.get('email_id')
        force = options.get('force', False)
        logger.info(
            f'Testing issue creation task for '
            f'email_id={email_id}, force={force}...'
        )
        try:
            # Use synchronous execution for command line
            result = create_issue_task.run(email_id, force=force)
            logger.info(f'Issue creation completed successfully: {result}')
        except Exception as e:
            logger.error(f'Error executing issue creation task: {e}')
            raise