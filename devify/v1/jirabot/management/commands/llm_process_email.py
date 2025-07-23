"""
Management command for testing llm_process_email task.
"""

from django.core.management.base import BaseCommand
import logging

from v1.jirabot.tasks import llm_process_email

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    Command to test llm_process_email task (process email with LLM).
    """
    help = (
        'Process email with LLM for summarization. '
        'Specify --email-id to process a specific email. '
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
            help='ID of the EmailMessage to process (required)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force reprocess even if already processed'
        )

    def handle(self, *args, **options):
        """
        Handle the command logic for testing llm_process_email.
        """
        email_id = options.get('email_id')
        force = options.get('force', False)
        logger.info(
            f'Testing llm_process_email task for email_id={email_id}, '
            f'force={force}...'
        )
        try:
            llm_process_email.run(email_id, force=force)
            logger.info('llm_process_email task executed successfully.')
        except Exception as e:
            logger.error(f'Error running llm_process_email: {e}')
        else:
            logger.info('llm_process_email task finished.')