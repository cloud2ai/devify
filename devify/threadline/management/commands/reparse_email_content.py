"""
Django management command to reparse email message raw content.

This command allows re-parsing of existing email messages' raw content to
extract text and HTML content, which is useful for messages that were
processed before content extraction was implemented.

Usage examples:
    # Reparse a single email (default mode)
    python manage.py reparse_email_content 123

    # Reparse with force (even if content exists)
    python manage.py reparse_email_content 123 --force

    # Batch processing with range
    python manage.py reparse_email_content 1-10 --batch

    # Reparse all emails (email_id not required)
    python manage.py reparse_email_content --all

    # Reparse only emails with specific status
    python manage.py reparse_email_content --all --status FETCHED

    # Dry run to see what would be processed
    python manage.py reparse_email_content --all --dry-run

    # Error: email_id is required unless using --all
    python manage.py reparse_email_content  # This will fail
"""

import logging
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from threadline.models import EmailMessage, EmailAttachment
from threadline.utils.email_client import EmailClient

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Management command to reparse email message raw content.

    This command processes a specific EmailMessage object and re-parses its
    raw_content to extract text_content and html_content fields.
    """

    help = 'Reparse email message raw content to extract text and HTML content'

    def add_arguments(self, parser):
        """
        Add command line arguments.
        """
        parser.add_argument(
            'email_id',
            type=int,
            nargs='?',
            help='Email message ID to reparse (required unless using --all)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force reparse even if content already exists'
        )
        parser.add_argument(
            '--batch',
            action='store_true',
            help='Process multiple emails (email_id can be a range like 1-10)'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Reparse all emails (use with caution)'
        )
        parser.add_argument(
            '--status',
            type=str,
            help='Only reparse emails with specific status (e.g., FETCHED)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without actually doing it'
        )

    def handle(self, *args, **options):
        """
        Execute the command.
        """
        email_id = options.get('email_id')
        force = options.get('force', False)
        batch = options.get('batch', False)
        all_emails = options.get('all', False)
        status_filter = options.get('status')
        dry_run = options.get('dry_run', False)

        # Validate arguments
        if not all_emails and not email_id:
            raise CommandError(
                'email_id is required unless using --all flag'
            )

        # Determine which emails to process
        if all_emails:
            emails = self._get_all_emails(status_filter)
        elif batch:
            if not email_id:
                raise CommandError('email_id is required for --batch mode')
            emails = self._get_batch_emails(email_id, status_filter)
        else:
            # Single email mode (default)
            emails = self._get_single_email(email_id)

        if not emails:
            self.stdout.write(
                self.style.WARNING('No emails found to process')
            )
            return

        if dry_run:
            self._show_dry_run(emails, force)
            return

        # Process emails
        success_count = 0
        error_count = 0

        for email in emails:
            try:
                if self._reparse_single_email(email, force):
                    success_count += 1
                    logger.info(f"Successfully reparsed email ID={email.id}")
                else:
                    logger.info(f"Skipped email ID={email.id}: {email.subject}")
            except Exception as e:
                error_count += 1
                logger.error(
                    f'Failed to reparse email ID={email.id}: {e}',
                    exc_info=True
                )

        # Summary - use stdout for final results
        self.stdout.write(
            self.style.SUCCESS(
                f'Processing complete: {success_count} successful, '
                f'{error_count} errors'
            )
        )
        logger.info(f"Command completed: {success_count} successful, "
                    f"{error_count} errors")

    def _get_single_email(self, email_id):
        """
        Get a single email by ID.
        """
        try:
            return [EmailMessage.objects.get(id=email_id)]
        except EmailMessage.DoesNotExist:
            raise CommandError(f'Email ID {email_id} does not exist')

    def _get_batch_emails(self, email_id, status_filter):
        """
        Get emails for batch processing.
        """
        # Support range format like "1-10" or single ID
        if isinstance(email_id, str) and '-' in str(email_id):
            start_id, end_id = map(int, str(email_id).split('-'))
            queryset = EmailMessage.objects.filter(
                id__gte=start_id,
                id__lte=end_id
            )
        else:
            # Single ID for batch mode
            queryset = EmailMessage.objects.filter(id=email_id)

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return list(queryset.order_by('id'))

    def _get_all_emails(self, status_filter):
        """
        Get all emails for processing.
        """
        queryset = EmailMessage.objects.all()

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return list(queryset.order_by('id'))

    def _show_dry_run(self, emails, force):
        """
        Show what would be processed in dry run mode.
        """
        self.stdout.write(
            self.style.WARNING(f'DRY RUN: Would process {len(emails)} emails')
        )

        for email in emails:
            has_content = bool(email.text_content and email.html_content)
            status = 'SKIP' if has_content and not force else 'PROCESS'

            self.stdout.write(
                f'  ID={email.id}: {email.subject[:50]}... '
                f'[{status}]'
            )

    def _reparse_single_email(self, email, force):
        """
        Reparse a single email message.
        """
        # Check if content already exists
        if not force and email.text_content and email.html_content:
            logger.info(f"Email ID {email.id} already has content, skipping")
            return False

        logger.info(f"Reparsing email ID={email.id}: {email.subject}")

        # Create a minimal EmailClient instance for parsing
        dummy_config = {
            'username': 'dummy',
            'password': 'dummy',
            'host': 'dummy',
            'port': 993,
            'use_ssl': True
        }
        dummy_filter_config = {}

        email_client = EmailClient(
            email_config=dummy_config,
            email_filter_config=dummy_filter_config,
            attachment_storage_path=settings.EMAIL_ATTACHMENT_STORAGE_PATH
        )

        # Convert raw_content to bytes for EmailClient parsing
        raw_content_bytes = email.raw_content.encode('utf-8')

        # Parse email using the unified method
        parsed_result = email_client.parse_email(raw_content_bytes)

        if not parsed_result:
            raise Exception(
                f'EmailClient failed to parse email ID={email.id}. '
                f'Parsing method failed.'
            )

        # Extract content from parsing result
        text_content = parsed_result.get('text_content', '')
        html_content = parsed_result.get('html_content', '')
        attachments = parsed_result.get('attachments', [])

        logger.info(f"Found {len(attachments)} attachments for email "
                    f"ID={email.id}")

        # Update email fields
        with transaction.atomic():
            email.text_content = text_content
            email.html_content = html_content
            email.updated_at = timezone.now()
            email.save(update_fields=[
                'text_content', 'html_content', 'updated_at'
            ])

            # Process attachments if any
            if attachments:
                logger.debug(f"Attachments: {attachments}")
                self._process_attachments(email, attachments)

        return True

    def _process_attachments(self, email, attachments):
        """
        Process attachments from parsed email result using smart comparison.

        Compares existing attachments with new ones to:
        - Keep existing attachments that are still valid
        - Update attachments that have changed
        - Remove attachments that no longer exist
        - Create new attachments

        Args:
            email: EmailMessage instance
            attachments: List of attachment info from parsing
        """
        # Use MD5 (safe_filename) as primary identifier for matching
        # MD5 ensures same content always has same identifier
        existing_attachments = {}
        for att in email.attachments.all():
            key = att.safe_filename  # Use MD5 as primary key
            existing_attachments[key] = att

        new_attachments = {}
        for att in attachments:
            key = att.get('safe_filename')  # Use MD5 as primary key
            new_attachments[key] = att

        # Find attachments to process
        to_delete = (
            set(existing_attachments.keys()) -
            set(new_attachments.keys())
        )
        to_create = (
            set(new_attachments.keys()) -
            set(existing_attachments.keys())
        )
        to_update = (
            set(existing_attachments.keys()) &
            set(new_attachments.keys())
        )

        logger.info(f"Attachment analysis for email ID={email.id}:")
        logger.info(f"  - To delete: {len(to_delete)}")
        logger.info(f"  - To create: {len(to_create)}")
        logger.info(f"  - To update: {len(to_update)}")

        # Delete attachments that no longer exist
        for key in to_delete:
            try:
                existing_attachment = existing_attachments[key]
                existing_attachment.delete()
                logger.info(f"Deleted attachment: "
                            f"{existing_attachment.filename} "
                            f"(MD5: {existing_attachment.safe_filename})")
            except Exception as e:
                logger.error(f"Failed to delete attachment {key}: {e}")

        # Update existing attachments that have changed
        for key in to_update:
            try:
                existing_attachment = existing_attachments[key]
                new_info = new_attachments[key]

                # Check if update is needed
                needs_update = (
                    existing_attachment.content_type !=
                        new_info['content_type']
                    or existing_attachment.file_size !=
                        new_info['file_size']
                    or existing_attachment.file_path !=
                        new_info['file_path']
                    or existing_attachment.is_image !=
                        new_info['is_image']
                )

                if needs_update:
                    existing_attachment.content_type = new_info['content_type']
                    existing_attachment.file_size = new_info['file_size']
                    existing_attachment.file_path = new_info['file_path']
                    existing_attachment.is_image = new_info['is_image']
                    existing_attachment.save(update_fields=[
                        'content_type', 'file_size', 'file_path',
                        'is_image'
                    ])
                    logger.info(f"Updated attachment: "
                                f"{existing_attachment.filename} "
                                f"(MD5: {existing_attachment.safe_filename})")
                else:
                    logger.debug(f"Attachment unchanged: "
                                f"{existing_attachment.filename} "
                                f"(MD5: {existing_attachment.safe_filename})")

            except Exception as e:
                logger.error(f"Failed to update attachment {key}: {e}")

        # Create new attachments
        for key in to_create:
            try:
                attachment_info = new_attachments[key]
                EmailAttachment.objects.create(
                    user=email.user,
                    email_message=email,
                    filename=attachment_info['filename'],
                    safe_filename=attachment_info['safe_filename'],
                    content_type=attachment_info['content_type'],
                    file_size=attachment_info['file_size'],
                    file_path=attachment_info['file_path'],
                    is_image=attachment_info['is_image']
                )
                logger.info(f"Created attachment: "
                            f"{attachment_info['filename']} "
                            f"(MD5: {attachment_info['safe_filename']})")

            except Exception as e:
                logger.error(
                    f"Failed to create attachment {key}: {e}"
                )
                # Continue processing other attachments
                continue