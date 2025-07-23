"""
Management command for testing submit_issue_to_jira task.
"""

from django.core.management.base import BaseCommand
import logging

from v1.jirabot.tasks import submit_issue_to_jira

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    Command to test submit_issue_to_jira task.
    """
    help = (
        'Submit processed issue info to JIRA for a given email_message_id.'
    )

    def add_arguments(self, parser):
        """
        Add command line arguments for the management command.
        """
        parser.add_argument(
            '--email-message-id',
            type=int,
            required=True,
            help='Email message ID to submit to JIRA (required)'
        )

    def handle(self, *args, **options):
        """
        Handle the command logic for testing submit_issue_to_jira.
        """
        email_message_id = options.get('email_message_id')
        logger.info(
            f'Testing submit_issue_to_jira task for '
            f'email_message_id={email_message_id}...'
        )
        try:
            # Synchronously call Celery task with context
            submit_issue_to_jira.run(email_message_id)
            logger.info('submit_issue_to_jira task executed successfully.')
        except Exception as e:
            logger.error(f'Error running submit_issue_to_jira: {e}')
        else:
            logger.info('submit_issue_to_jira task finished.')