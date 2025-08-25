"""
Management command for testing LLM-related email processing tasks.
"""

from django.core.management.base import BaseCommand
import logging

from threadline.tasks import (
    organize_attachments_ocr_task,
    organize_email_body_task,
    summarize_email_task
)

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    Command to test LLM-related email processing tasks.
    """
    help = (
        'Process email with LLM tasks: Attachments -> Email Body -> Summary. '
        'Specify --email-id to process a specific email. '
        'Use --force to reprocess even if already processed. '
        'Use --task to specify which LLM task to run.'
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
        parser.add_argument(
            '--task',
            choices=['attachments', 'email', 'summary', 'all'],
            default='all',
            help='Specific LLM task to run (default: all)'
        )

    def handle(self, *args, **options):
        """
        Handle the command logic for testing LLM-related email processing tasks.
        """
        email_id = options.get('email_id')
        force = options.get('force', False)
        task = options.get('task', 'all')

        logger.info(
            f'Testing LLM email processing tasks for email_id={email_id}, '
            f'force={force}, task={task}...'
        )

        try:
            if task == 'all':
                # Run all LLM tasks in sequence
                logger.info('Running all LLM tasks in sequence...')

                # Attachments OCR organization
                logger.info('Starting attachments OCR organization...')
                attachments_result = organize_attachments_ocr_task.run(email_id, force=force)
                logger.info(f'Attachments task completed successfully')

                # Email body organization
                logger.info('Starting email body organization...')
                email_result = organize_email_body_task.run(email_id, force=force)
                logger.info(f'Email body task completed successfully')

                # Email summarization
                logger.info('Starting email summarization...')
                summary_result = summarize_email_task.run(email_id, force=force)
                logger.info(f'Summary task completed successfully')

                logger.info('All LLM tasks have been completed successfully.')

            elif task == 'attachments':
                logger.info('Starting attachments OCR organization...')
                result = organize_attachments_ocr_task.run(email_id, force=force)
                logger.info(f'Attachments task completed successfully')

            elif task == 'email':
                logger.info('Starting email body organization...')
                result = organize_email_body_task.run(email_id, force=force)
                logger.info(f'Email body task completed successfully')

            elif task == 'summary':
                logger.info('Starting email summarization...')
                result = summarize_email_task.run(email_id, force=force)
                logger.info(f'Summary task completed successfully')

        except Exception as e:
            logger.error(f'Error executing LLM task(s): {e}')
            raise
        else:
            logger.info('LLM email processing task command finished successfully.')