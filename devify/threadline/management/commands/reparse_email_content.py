"""
Django management command to reparse email message raw content.

This command allows re-parsing of existing email messages' raw content to
extract text and HTML content, which is useful for messages that were
processed before content extraction was implemented.
"""

import logging
from django.core.management.base import BaseCommand, CommandError
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
            help='Email message ID to reparse'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force reparse even if content already exists'
        )

    def handle(self, *args, **options):
        """
        Execute the command.
        """
        email_id = options['email_id']
        force = options.get('force')

        try:
            email = EmailMessage.objects.get(id=email_id)
        except EmailMessage.DoesNotExist:
            raise CommandError(f'Email ID {email_id} does not exist')

        # Check if content already exists
        if not force and email.text_content and email.html_content:
            self.stdout.write(
                self.style.WARNING(
                    f'Email ID {email_id} already has content. '
                    f'Use --force to reparse anyway.'
                )
            )
            return

        self.stdout.write(
            f'Reparsing email ID={email_id}: {email.subject}'
        )

        try:
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
                email_filter_config=dummy_filter_config
            )

            # Convert raw_content to bytes for EmailClient parsing
            raw_content_bytes = email.raw_content.encode('utf-8')

            # Parse email using the unified method
            parsed_result = email_client.parse_email(raw_content_bytes)

            if not parsed_result:
                raise Exception(
                    f'EmailClient failed to parse email ID={email_id}. '
                    f'Parsing method failed.'
                )

            # Extract content from parsing result
            text_content = parsed_result.get('text_content', '')
            html_content = parsed_result.get('html_content', '')
            attachments = parsed_result.get('attachments', [])

            logger.info(f"in reparse_email_content: Found {len(attachments)} "
                        f"attachments")

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

            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully reparsed email ID={email_id}'
                )
            )

        except Exception as e:
            logger.error(
                f'Failed to reparse email ID={email_id}: {e}',
                exc_info=True
            )
            raise CommandError(
                f'Failed to reparse email ID={email_id}: {e}'
            )

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
                self.stdout.write(f"Deleted attachment: "
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
                    self.stdout.write(f"Updated attachment: "
                                      f"{existing_attachment.filename} "
                                      f"(MD5: {existing_attachment.safe_filename})")
                else:
                    logger.info(f"Attachment unchanged: "
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
                self.stdout.write(f"Created attachment: "
                                  f"{attachment_info['filename']} "
                                  f"(MD5: {attachment_info['safe_filename']})")

            except Exception as e:
                logger.error(
                    f"Failed to create attachment {key}: {e}"
                )
                # Continue processing other attachments
                continue