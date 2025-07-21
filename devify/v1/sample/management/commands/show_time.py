"""
Management command to test show_current_time Celery task
without starting Celery worker.

This command allows testing of the show_current_time task
in a synchronous manner, useful for development and
debugging purposes.

Usage:
    python manage.py show_time [--debug]

Examples:
    python manage.py show_time
    # Show current time

    python manage.py show_time --debug
    # Show current time with debug logging
"""

from django.core.management.base import BaseCommand, CommandError

from django.db import transaction

import logging

import sys

from v1.sample.tasks import show_current_time

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Management command to test show_current_time Celery task
    synchronously.

    This command provides a way to test the show_current_time
    task without needing to start a Celery worker. It's useful
    for development, debugging, and testing task logic.
    """

    help = (
        'Test show_current_time Celery task without starting '
        'Celery worker. Useful for development and debugging.'
    )

    def add_arguments(self, parser):
        """
        Add command line arguments.

        Args:
            parser: ArgumentParser instance
        """
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable debug logging level'
        )

        parser.add_argument(
            '--verbose',
            action='store_true',
            help=(
                'Enable verbose output (deprecated, use --debug '
                'instead)'
            )
        )

    def handle(self, *args, **options):
        """
        Execute the management command.

        Args:
            *args: Additional arguments
            **options: Command options

        Raises:
            CommandError: If task fails
        """
        debug = options['debug']
        verbose = options['verbose']

        # Setup logging configuration
        self._setup_logging(debug or verbose)

        logger.info('Starting show_current_time task')

        try:
            with transaction.atomic():
                self._run_show_current_time_task()
        except Exception as e:
            logger.error(
                f'Task execution failed: {str(e)}'
            )
            raise CommandError(
                f'Task execution failed: {str(e)}'
            )

    def _setup_logging(self, debug_mode=False):
        """
        Setup logging configuration for the command.

        Args:
            debug_mode (bool): Whether to enable debug logging
        """
        # Configure logging format
        log_format = (
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        if debug_mode:
            log_level = logging.DEBUG
            logger.info('Debug logging enabled')
        else:
            log_level = logging.INFO
            logger.info('Info logging enabled')

        # Configure console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(
            logging.Formatter(log_format)
        )

        # Configure logger
        logger.setLevel(log_level)
        logger.handlers.clear()
        logger.addHandler(console_handler)
        logger.propagate = False

    def _run_show_current_time_task(self):
        """
        Execute the show_current_time task.

        This method calls the show_current_time task function
        directly and displays the results.
        """
        logger.info('Running show_current_time task...')

        try:
            show_current_time()
            logger.info(
                'Show current time task completed successfully!'
            )
        except Exception as e:
            logger.error(
                f'Show current time task failed: {str(e)}'
            )
            raise