"""
Management command for email-related tests and operations.
"""

import logging
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from v1.jirabot.models import Settings
from v1.jirabot.utils.email_client import EmailClient
from core.settings.globals import EMAIL_ATTACHMENT_STORAGE_PATH

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    Command to test email connection, configuration, and IMAP listing for a
    specific user.
    """
    help = (
        'Test email connection/configuration or list IMAP emails for a user. '
        'Use --mode config or --mode imap.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            required=True,
            help='Username to operate on',
        )
        parser.add_argument(
            '--mode',
            type=str,
            choices=['config', 'imap'],
            required=True,
            help=(
                'Operation mode: config (test config/connection) or '
                'imap (list emails)'
            ),
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=10,
            help='Maximum number of emails to fetch in imap mode '
                 '(default: 10)',
        )
        parser.add_argument(
            '--folder',
            type=str,
            default='INBOX',
            help='IMAP folder to fetch emails from (default: INBOX)',
        )
        parser.add_argument(
            '--test-connection',
            action='store_true',
            help='Test actual connection to email server (only for config mode)',
        )

    def handle(self, *args, **options):
        username = options['user']
        mode = options['mode']
        limit = options['limit']
        folder = options['folder']
        test_connection = options['test_connection']

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            logger.error(
                f'User "{username}" does not exist'
            )
            raise CommandError(
                f'User "{username}" does not exist'
            )

        try:
            email_setting = user.settings.get(
                key='email_config',
                is_active=True
            )
            filter_setting = user.settings.get(
                key='email_filter_config',
                is_active=True
            )
            email_config = email_setting.value
            email_filter_config = filter_setting.value
        except Settings.DoesNotExist as e:
            logger.error(
                f'Missing required settings for user {username}: {e}'
            )
            raise CommandError(
                f'Missing required settings for user {username}: {e}'
            )

        if mode == 'config':
            # Display configuration
            logger.info('📧 Email Configuration:')
            logger.info(
                f'  SMTP Host: {email_config.get("host")})'
            )
            logger.info(
                f'  IMAP Host: {email_config.get("imap_host")})'
            )
            logger.info(
                f'  IMAP Port: {email_config.get("imap_ssl_port")})'
            )
            logger.info(
                f'  Username: {email_config.get("username")})'
            )
            logger.info(
                f'  Use SSL: {email_config.get("use_ssl")})'
            )
            logger.info('📁 Filter Configuration:')
            logger.info(
                f'  Folder: {email_filter_config.get("folder")})'
            )
            logger.info(
                f'  Filters: {email_filter_config.get("filters")})'
            )
            logger.info(
                f'  Max Age Days: {email_filter_config.get("max_age_days")})'
            )
            scanner = EmailClient(
                email_config,
                email_filter_config,
                EMAIL_ATTACHMENT_STORAGE_PATH
            )
            logger.info('✅ EmailClient initialized successfully')
            logger.info(
                f'  Search Criteria: {scanner.search_criteria}'
            )
            if test_connection:
                logger.info('🔗 Testing connection...')
                try:
                    if scanner.connect():
                        logger.info(
                            '✅ Successfully connected to email server'
                        )
                        folder = scanner.folder
                        logger.info(
                            f'  Selected folder: {folder}'
                        )
                        scanner.disconnect()
                        logger.info('  Disconnected from server')
                    else:
                        logger.error(
                            '❌ Failed to connect to email server'
                        )
                except Exception as e:
                    logger.error(
                        f'❌ Connection error: {e}'
                    )
            else:
                logger.info(
                    '💡 Use --test-connection to test actual connection'
                )
            logger.info(
                '✅ Email configuration test completed successfully'
            )
        elif mode == 'imap':
            # Override folder in filter config
            email_filter_config = dict(email_filter_config)
            email_filter_config['folder'] = folder
            logger.info(
                f'Connecting to IMAP for user: {username}'
            )
            scanner = EmailClient(
                email_config,
                email_filter_config,
                EMAIL_ATTACHMENT_STORAGE_PATH
            )
            count = 0
            for email in scanner.scan_emails():
                count += 1
                logger.info(f"\n--- Email #{count} ---")
                logger.info(
                    f"Subject: {email.get('subject')}"
                )
                text_content = email.get('text_content', '')
                html_content = email.get('html_content', '')
                raw_content = email.get('raw_content', '')
                logger.info(
                    f"Text Content (first 100): {text_content[:100]}"
                )
                logger.info(
                    f"HTML Content (first 100): {html_content[:100]}"
                )
                logger.info(
                    f"Raw Content (first 200): {raw_content[:200]}"
                )
                logger.info(
                    f"From: {email.get('sender')}"
                )
                logger.info(
                    f"Date: {email.get('received_at')}"
                )
                logger.info(
                    f"Attachments: {len(email.get('attachments', []))}"
                )
                for i, att in enumerate(email.get('attachments', [])):
                    logger.info(
                        f"  Attachment #{i+1}:"
                    )
                    logger.info(
                        f"    Filename: {att.get('filename')}"
                    )
                    logger.info(
                        f"    Content-Type: {att.get('content_type')}"
                    )
                    logger.info(
                        f"    Size: {att.get('file_size')} bytes"
                    )
                    logger.info(
                        f"    File Path: {att.get('file_path')}"
                    )
                    logger.info(
                        f"    Is Image: {att.get('is_image')}"
                    )
                if count >= limit:
                    break
            if count == 0:
                logger.info('No emails found.')
            else:
                logger.info(
                    f'Total emails listed: {count}'
                )