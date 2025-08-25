"""
Management command for testing submit_issue_to_jira task.
"""

from django.core.management.base import BaseCommand
import logging

from threadline.tasks import submit_issue_to_jira

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    Command to test submit_issue_to_jira task.
    """
    help = (
        'Submit processed issue info to JIRA for a given email_id. '
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
            help='Email message ID to submit to JIRA (required)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force reprocess even if already processed'
        )

    def handle(self, *args, **options):
        """
        Handle the command logic for testing submit_issue_to_jira.
        """
        email_id = options.get('email_id')
        force = options.get('force', False)
        logger.info(
            f'Testing submit_issue_to_jira task for '
            f'email_id={email_id}, force={force}...'
        )
        try:
            # Use synchronous execution for command line
            result = submit_issue_to_jira.run(email_id, force=force)
        except Exception as e:
            logger.error(f'Error executing submit_issue_to_jira: {e}')
            raise