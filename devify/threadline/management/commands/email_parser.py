"""
Django management command for email parsing

This command provides a unified interface for parsing emails from
different sources:
- EML files (for testing and debugging)
- Database raw_content (for reprocessing existing emails)

Usage examples:
    # Parse EML files
    python manage.py email_parser file email.eml
    python manage.py email_parser file *.eml --summary
    python manage.py email_parser file email.eml --compare

    # Reparse database emails
    python manage.py email_parser db 123
    python manage.py email_parser db --all
    python manage.py email_parser db 1-10 --batch
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from threadline.models import EmailAttachment, EmailMessage
from threadline.utils.email_flanker_parser import EmailFlankerParser
from threadline.utils.email_parser import EmailParser

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Unified email parsing command for files and database content'

    def add_arguments(self, parser):
        # Source type (file or database)
        parser.add_argument(
            'source',
            choices=['file', 'db'],
            help='Email source: file (EML files) or db '
                 '(database raw_content)'
        )

        # Source identifier
        parser.add_argument(
            'identifier',
            nargs='?',
            help='Source identifier: EML file path(s) for file mode, '
                 'email ID for db mode'
        )

        # Parser type selection
        parser.add_argument(
            '--parser',
            choices=['legacy', 'flanker', 'both'],
            default='flanker',
            help='Email parser to use: legacy (EmailParser), '
                 'flanker (EmailFlankerParser), or both for comparison '
                 '(default: flanker)'
        )

        # Output options
        parser.add_argument(
            '-o', '--output-dir',
            type=str,
            help='Directory to save attachments (file mode only)'
        )
        parser.add_argument(
            '--summary',
            action='store_true',
            help='Show only summary information (compact output)'
        )
        parser.add_argument(
            '--detail',
            action='store_true',
            help='Enable detailed output with additional information'
        )
        parser.add_argument(
            '--text',
            action='store_true',
            help='Show complete text content (not just preview)'
        )
        parser.add_argument(
            '--html',
            action='store_true',
            help='Show complete HTML content (not just preview)'
        )
        parser.add_argument(
            '--text-only',
            action='store_true',
            help='Output only the parsed text content '
                 '(no headers or formatting)'
        )
        parser.add_argument(
            '--json',
            action='store_true',
            help='Export parsing results to JSON files '
                 '(file mode only)'
        )

        # Comparison and validation
        parser.add_argument(
            '--compare',
            action='store_true',
            help='Compare results between legacy and flanker parsers'
        )
        parser.add_argument(
            '--validate',
            type=str,
            help='JSON file with expected results for validation '
                 '(file mode only)'
        )

        # Database-specific options
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force reparse even if content already exists '
                 '(db mode only)'
        )
        parser.add_argument(
            '--batch',
            action='store_true',
            help='Process multiple emails (db mode only, identifier '
                 'can be a range like 1-10)'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Reparse all emails (db mode only, use with caution)'
        )
        parser.add_argument(
            '--status',
            type=str,
            help='Only reparse emails with specific status '
                 '(db mode only, e.g., FETCHED)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without actually '
                 'doing it (db mode only)'
        )
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable debug logging for detailed output'
        )

    def handle(self, *args, **options):
        """Main command handler"""
        # Set debug logging level if debug flag is enabled
        if options.get('debug', False):
            logging.getLogger().setLevel(logging.DEBUG)
            logger.info('Debug logging enabled')

        source = options['source']
        identifier = options.get('identifier')

        # Store options as instance variables
        self.parser_type = options.get('parser', 'flanker')
        self.summary_only = options.get('summary', False)
        self.detail = options.get('detail', False)
        self.show_full_text = options.get('text', False)
        self.show_full_html = options.get('html', False)
        self.text_only = options.get('text_only', False)
        self.compare_parsers = options.get('compare', False)
        self.json_export = options.get('json', False)
        self.validation_file = options.get('validate')
        self.output_dir = options.get('output_dir')

        # Database-specific options
        self.force = options.get('force', False)
        self.batch = options.get('batch', False)
        self.all_emails = options.get('all', False)
        self.status_filter = options.get('status')
        self.dry_run = options.get('dry_run', False)

        # Route to appropriate handler
        if source == 'file':
            self._handle_file_mode(identifier)
        elif source == 'db':
            self._handle_database_mode(identifier)

    def _handle_file_mode(self, identifier):
        """Handle EML file parsing mode"""
        if not identifier:
            raise CommandError("File path(s) required for file mode")

        # Load validation data if provided
        validation_data = None
        if self.validation_file:
            validation_data = self._load_validation_data(
                self.validation_file
            )

        # Expand file patterns
        eml_files = self._expand_file_patterns(identifier.split())

        if not eml_files:
            raise CommandError("No EML files found to process")

        self._print_header(len(eml_files), "EML Files")

        success_count = 0
        total_count = len(eml_files)

        for eml_file in eml_files:
            try:
                if self._process_eml_file(eml_file, validation_data):
                    success_count += 1

                # Add separator between files if processing multiple
                should_show_separator = (
                    total_count > 1 and
                    not self.summary_only and
                    not self.text_only
                )
                if should_show_separator:
                    self.stdout.write("-" * 80)

            except Exception as e:
                error_msg = f"❌ Error processing {eml_file}: {e}"
                self.stdout.write(self.style.ERROR(error_msg))
                if self.detail:
                    import traceback
                    self.stdout.write(traceback.format_exc())

        self._print_summary(success_count, total_count)

    def _handle_database_mode(self, identifier):
        """Handle database email reparsing mode"""
        # Validate arguments
        if not self.all_emails and not identifier:
            raise CommandError(
                'Email ID is required unless using --all flag'
            )

        # Determine which emails to process
        if self.all_emails:
            emails = self._get_all_emails()
        elif self.batch:
            emails = self._get_batch_emails(identifier)
        else:
            emails = self._get_single_email(identifier)

        if not emails:
            self.stdout.write(
                self.style.WARNING('No emails found to process')
            )
            return

        if self.dry_run:
            self._show_dry_run(emails)
            return

        self._print_header(len(emails), "Database Emails")

        success_count = 0
        error_count = 0

        for email in emails:
            try:
                if self._reparse_single_email(email):
                    success_count += 1
                    logger.info(
                        f"Successfully reparsed email ID={email.id}"
                    )
                else:
                    logger.info(
                        f"Skipped email ID={email.id}: {email.subject}"
                    )
            except Exception as e:
                error_count += 1
                logger.error(
                    f'Failed to reparse email ID={email.id}: {e}',
                    exc_info=True
                )
                self.stdout.write(
                    self.style.ERROR(
                        f"❌ Failed to reparse email ID={email.id}: {e}"
                    )
                )

        self._print_summary(success_count, len(emails))

    # File mode methods
    def _expand_file_patterns(self, patterns: List[str]) -> List[Path]:
        """Expand file patterns and return list of existing EML files"""
        eml_files = []

        for pattern in patterns:
            if '*' in pattern or '?' in pattern:
                # Handle glob patterns
                expanded = list(Path().glob(pattern))
                eml_files.extend([
                    f for f in expanded
                    if f.suffix.lower() == '.eml'
                ])
            else:
                # Handle direct file paths
                file_path = Path(pattern)
                if file_path.exists():
                    if file_path.suffix.lower() != '.eml':
                        warning_msg = (
                            f"⚠️  Warning: {pattern} doesn't have "
                            f".eml extension"
                        )
                        self.stdout.write(
                            self.style.WARNING(warning_msg)
                        )
                    eml_files.append(file_path)
                else:
                    error_msg = f"❌ File not found: {pattern}"
                    self.stdout.write(self.style.ERROR(error_msg))

        return sorted(eml_files)

    def _process_eml_file(
        self, eml_file: Path, validation_data: Dict = None
    ) -> bool:
        """Process a single EML file"""
        # Setup attachment directory
        if self.output_dir:
            attachment_dir = Path(self.output_dir)
        else:
            attachment_dir = (
                eml_file.parent / f"{eml_file.stem}_attachments"
            )

        attachment_dir.mkdir(exist_ok=True)

        if not self.summary_only and not self.text_only:
            parsing_msg = (
                f"🔍 Parsing: {self.style.SUCCESS(str(eml_file))}"
            )
            self.stdout.write(parsing_msg)
            self.stdout.write(f"📁 Attachments: {attachment_dir}")
            self.stdout.write("=" * 80)

        try:
            # Parse file based on selected method
            if self.compare_parsers or self.parser_type == 'both':
                result = self._parse_with_comparison(
                    eml_file, attachment_dir
                )
            else:
                result = self._parse_with_direct_parser(
                    eml_file, attachment_dir
                )

            if result is None:
                self.stdout.write(
                    self.style.ERROR("❌ Failed to parse EML file")
                )
                return False

            # Display results based on mode
            if self.text_only:
                self._display_text_only(result)
            elif self.summary_only:
                self._display_summary(eml_file, result)
            else:
                self._display_detailed_results(result)

            # Export to JSON if requested
            if self.json_export:
                self._export_to_json(eml_file, result, attachment_dir)

            # Validate against expected results if provided
            if validation_data:
                self._validate_results(eml_file, result, validation_data)

            if not self.summary_only and not self.text_only:
                success_msg = "✅ Parsing completed successfully!"
                self.stdout.write(self.style.SUCCESS(success_msg))

            return True

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Parsing failed: {e}"))
            if self.detail:
                import traceback
                self.stdout.write(traceback.format_exc())
            return False

    def _parse_with_direct_parser(
        self, eml_file: Path, attachment_dir: Path
    ) -> Dict[str, Any]:
        """Parse using direct parser (legacy or flanker)"""
        if self.parser_type == 'legacy':
            parser = EmailParser(str(attachment_dir))
            parser_name = "EmailParser (Legacy)"
        else:  # flanker
            parser = EmailFlankerParser(str(attachment_dir))
            parser_name = "EmailFlankerParser (Enhanced)"

        if not self.summary_only and not self.text_only:
            self.stdout.write(f"🔧 Using: {parser_name}")

        return parser.parse_from_file(str(eml_file))

    def _parse_with_comparison(
        self, eml_file: Path, attachment_dir: Path
    ) -> Dict[str, Any]:
        """Parse with both parsers and compare results"""
        if not self.summary_only and not self.text_only:
            self.stdout.write("🔧 Comparing Legacy vs Flanker Parsers")
            self.stdout.write("=" * 50)

        # Parse with legacy parser
        legacy_parser = EmailParser(str(attachment_dir))
        legacy_result = legacy_parser.parse_from_file(str(eml_file))

        # Parse with flanker parser
        flanker_parser = EmailFlankerParser(str(attachment_dir))
        flanker_result = flanker_parser.parse_from_file(str(eml_file))

        if legacy_result is None and flanker_result is None:
            return None

        # Display comparison if not in text-only or summary mode
        if not self.summary_only and not self.text_only:
            self._display_parser_comparison(
                legacy_result, flanker_result
            )

        # Return flanker result by default (as it's the new default)
        return (
            flanker_result if flanker_result is not None
            else legacy_result
        )

    # Database mode methods (from reparse_email_content)
    def _get_single_email(self, email_id):
        """Get a single email by ID."""
        try:
            return [EmailMessage.objects.get(id=email_id)]
        except EmailMessage.DoesNotExist:
            raise CommandError(f'Email ID {email_id} does not exist')

    def _get_batch_emails(self, email_id, status_filter=None):
        """Get emails for batch processing."""
        # Support range format like "1-10" or single ID
        if isinstance(email_id, str) and '-' in str(email_id):
            start_id, end_id = map(int, str(email_id).split('-'))
            queryset = EmailMessage.objects.filter(
                id__gte=start_id, id__lte=end_id
            )
        else:
            queryset = EmailMessage.objects.filter(id=email_id)

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return list(queryset.order_by('id'))

    def _get_all_emails(self, status_filter=None):
        """Get all emails for processing."""
        queryset = EmailMessage.objects.all()

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return list(queryset.order_by('id'))

    def _show_dry_run(self, emails):
        """Show what would be processed in dry run mode."""
        self.stdout.write(
            self.style.WARNING(
                f'DRY RUN: Would process {len(emails)} emails'
            )
        )

        for email in emails:
            has_content = bool(email.text_content and email.html_content)
            status = (
                'SKIP' if has_content and not self.force else 'PROCESS'
            )

            self.stdout.write(
                f'  ID={email.id}: {email.subject[:50]}... [{status}]'
            )

    def _reparse_single_email(self, email):
        """Reparse a single email message."""
        # Check if content already exists
        if not self.force and email.text_content and email.html_content:
            logger.info(
                f"Email ID {email.id} already has content, skipping"
            )
            return False

        logger.info(f"Reparsing email ID={email.id}: {email.subject}")

        # Use direct parser instead of EmailProcessor
        attachment_dir = getattr(
            settings, 'EMAIL_ATTACHMENT_STORAGE_PATH', '/tmp/attachments'
        )

        if self.parser_type == 'legacy':
            parser = EmailParser(attachment_dir)
        else:
            parser = EmailFlankerParser(attachment_dir)

        # Parse email content
        parsed_result = parser.parse_from_string(email.raw_content)

        if not parsed_result:
            raise Exception(
                f'Parser failed to parse email ID={email.id}'
            )

        # Extract content from parsing result
        text_content = parsed_result.get('text_content', '')
        html_content = parsed_result.get('html_content', '')
        attachments = parsed_result.get('attachments', [])

        logger.info(
            f"Found {len(attachments)} attachments for email ID={email.id}"
        )

        # Update email fields
        with transaction.atomic():
            email.text_content = text_content
            email.html_content = html_content
            email.updated_at = timezone.now()
            email.save(
                update_fields=[
                    'text_content', 'html_content', 'updated_at'
                ]
            )

            # Process attachments if any
            if attachments:
                self._process_attachments(email, attachments)

        return True

    def _process_attachments(self, email, attachments):
        """Process attachments from parsed email result using
        smart comparison."""
        # Use MD5 (safe_filename) as primary identifier for matching
        existing_attachments = {}
        for att in email.attachments.all():
            key = att.safe_filename
            existing_attachments[key] = att

        new_attachments = {}
        for att in attachments:
            key = att.get('safe_filename')
            new_attachments[key] = att

        # Find attachments to process
        to_delete = (
            set(existing_attachments.keys()) - set(new_attachments.keys())
        )
        to_create = (
            set(new_attachments.keys()) - set(existing_attachments.keys())
        )
        to_update = (
            set(existing_attachments.keys()) & set(new_attachments.keys())
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
                logger.info(
                    f"Deleted attachment: {existing_attachment.filename} "
                    f"(MD5: {existing_attachment.safe_filename})"
                )
            except Exception as e:
                logger.error(f"Failed to delete attachment {key}: {e}")

        # Update existing attachments that have changed
        for key in to_update:
            try:
                existing_attachment = existing_attachments[key]
                new_info = new_attachments[key]

                needs_update = (
                    existing_attachment.content_type != new_info[
                        'content_type'
                    ]
                    or existing_attachment.file_size != new_info['file_size']
                    or existing_attachment.file_path != new_info['file_path']
                    or existing_attachment.is_image != new_info['is_image']
                )

                if needs_update:
                    existing_attachment.content_type = new_info['content_type']
                    existing_attachment.file_size = new_info['file_size']
                    existing_attachment.file_path = new_info['file_path']
                    existing_attachment.is_image = new_info['is_image']
                    existing_attachment.save(
                        update_fields=[
                            'content_type', 'file_size', 'file_path',
                            'is_image'
                        ]
                    )
                    logger.info(
                        f"Updated attachment: {existing_attachment.filename} "
                        f"(MD5: {existing_attachment.safe_filename})"
                    )

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
                logger.info(
                    f"Created attachment: {attachment_info['filename']} "
                    f"(MD5: {attachment_info['safe_filename']})"
                )

            except Exception as e:
                logger.error(f"Failed to create attachment {key}: {e}")
                continue

    # Shared display methods
    def _display_text_only(self, result: Dict[str, Any]):
        """Display only the parsed text content"""
        text_content = result.get('text_content', '')
        if text_content:
            self.stdout.write(text_content)

    def _display_summary(self, source, result: Dict[str, Any]):
        """Display summary information only"""
        text_len = len(result.get('text_content', ''))
        html_len = len(result.get('html_content', ''))
        attachments_count = len(result.get('attachments', []))
        image_count = result.get('text_content', '').count('[IMAGE:')

        if isinstance(source, Path):
            source_name = source.name
        else:
            source_name = f"ID={source.id}"

        summary_line = (
            f"📧 {source_name:<30} | "
            f"📝 {text_len:>5}c | "
            f"🌐 {html_len:>5}c | "
            f"📎 {attachments_count:>2} | "
            f"🖼️  {image_count:>2} | "
            f"✅"
        )
        self.stdout.write(summary_line)

    def _display_detailed_results(self, result: Dict[str, Any]):
        """Display detailed parsing results"""
        # Basic information
        self.stdout.write(f"📧 Subject: {result.get('subject', 'N/A')}")
        self.stdout.write(f"📤 From: {result.get('sender', 'N/A')}")
        self.stdout.write(f"📥 To: {result.get('recipients', 'N/A')}")
        self.stdout.write(f"📅 Date: {result.get('received_at', 'N/A')}")
        self.stdout.write(f"🆔 Message ID: {result.get('message_id', 'N/A')}")

        # Content analysis
        text_content = result.get('text_content', '')
        html_content = result.get('html_content', '')

        self.stdout.write(f"\n📊 Content Analysis:")
        text_len = len(text_content)
        html_len = len(html_content)
        self.stdout.write(f"   📝 Text Content: {text_len} characters")
        self.stdout.write(f"   🌐 HTML Content: {html_len} characters")

        # Text content display
        if text_content:
            if self.show_full_text:
                self.stdout.write(f"\n📄 Complete Text Content:")
                self.stdout.write("=" * 60)
                self.stdout.write(text_content)
                self.stdout.write("=" * 60)
            else:
                self.stdout.write(f"\n📄 Text Content Preview:")
                preview_length = 400 if self.detail else 200
                preview = text_content[:preview_length]
                if len(text_content) > preview_length:
                    preview += "..."
                self.stdout.write(preview)

            # Count image placeholders
            image_count = text_content.count('[IMAGE:')
            if image_count > 0:
                image_msg = f"\n🖼️  Image placeholders found: {image_count}"
                self.stdout.write(image_msg)

        # HTML content display
        if html_content and (self.detail or self.show_full_html):
            if self.show_full_html:
                self.stdout.write(f"\n🌐 Complete HTML Content:")
                self.stdout.write("=" * 60)
                self.stdout.write(html_content)
                self.stdout.write("=" * 60)
            else:
                self.stdout.write(f"\n🌐 HTML Content Preview:")
                if len(html_content) > 300:
                    html_preview = html_content[:300] + "..."
                else:
                    html_preview = html_content
                self.stdout.write(html_preview)

        # Attachments
        attachments = result.get('attachments', [])
        if attachments:
            self.stdout.write(f"\n📎 Attachments ({len(attachments)}):")
            for i, att in enumerate(attachments, 1):
                filename = att.get('filename', 'Unknown')
                safe_filename = att.get('safe_filename', 'Unknown')
                content_type = att.get('content_type', 'Unknown')
                file_size = att.get('file_size', 0)
                is_image = att.get('is_image', False)
                file_path = att.get('file_path', '')

                # Format file size
                size_str = self._format_file_size(file_size)
                type_icon = "🖼️" if is_image else "📄"

                self.stdout.write(f"   {i}. {type_icon} {filename}")
                self.stdout.write(f"      → {safe_filename}")
                self.stdout.write(f"      📏 {size_str} | {content_type}")

                # Check if file exists
                if file_path and Path(file_path).exists():
                    self.stdout.write(f"      ✅ File saved successfully")
                elif file_path:
                    self.stdout.write(f"      ❌ File not found on disk")
        else:
            self.stdout.write(f"\n📎 No attachments found")

    def _display_parser_comparison(
        self,
        legacy_result: Dict[str, Any],
        flanker_result: Dict[str, Any]
    ):
        """Display comparison between legacy and flanker parsers"""
        self.stdout.write("\n📊 Parser Comparison:")
        self.stdout.write("-" * 50)

        # Basic field comparison
        fields_to_compare = ['subject', 'sender', 'recipients', 'message_id']

        for field in fields_to_compare:
            legacy_val = legacy_result.get(field, '') if legacy_result else ''
            flanker_val = (
                flanker_result.get(field, '') if flanker_result else ''
            )
            match = "✅" if legacy_val == flanker_val else "❌"
            self.stdout.write(f"   {field.title()}: {match}")

        # Content analysis
        if legacy_result and flanker_result:
            legacy_text_len = len(legacy_result.get('text_content', ''))
            flanker_text_len = len(flanker_result.get('text_content', ''))
            legacy_html_len = len(legacy_result.get('html_content', ''))
            flanker_html_len = len(flanker_result.get('html_content', ''))
            legacy_attachments = len(legacy_result.get('attachments', []))
            flanker_attachments = len(flanker_result.get('attachments', []))

            self.stdout.write(f"\n📈 Content Analysis:")
            self.stdout.write(
                f"   Text Content: {legacy_text_len} → "
                f"{flanker_text_len} chars"
            )
            self.stdout.write(
                f"   HTML Content: {legacy_html_len} → "
                f"{flanker_html_len} chars"
            )
            self.stdout.write(
                f"   Attachments: {legacy_attachments} → {flanker_attachments}"
            )

            # Check for improvement
            if flanker_text_len > legacy_text_len:
                improvement = (
                    (flanker_text_len - legacy_text_len) /
                    max(legacy_text_len, 1)
                ) * 100
                self.stdout.write(
                    f"   📈 Text content improved by {improvement:.1f}%"
                )
            elif flanker_text_len < legacy_text_len:
                decrease = (
                    (legacy_text_len - flanker_text_len) /
                    max(legacy_text_len, 1)
                ) * 100
                self.stdout.write(
                    f"   📉 Text content decreased by {decrease:.1f}%"
                )

        self.stdout.write("=" * 50)

    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0B"

        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        size = float(size_bytes)

        while size >= 1024 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1

        return f"{size:.1f}{size_names[i]}"

    def _export_to_json(self, eml_file: Path, result: Dict[str, Any],
                       attachment_dir: Path):
        """
        Export simplified parsing results to JSON file.

        Args:
            eml_file: Path to the EML file being processed
            result: Parsing result dictionary
            attachment_dir: Directory for attachments
                (unused in simplified mode)
        """
        json_file = eml_file.parent / f"{eml_file.stem}.json"

        simplified_result = self._create_simplified_result(result)

        try:
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(simplified_result, f, indent=2, ensure_ascii=False)

            self.stdout.write(f"Simplified results exported to: {json_file}")

        except Exception as e:
            warning_msg = f"Failed to export JSON: {e}"
            self.stdout.write(self.style.WARNING(warning_msg))

    def _create_simplified_result(
        self, result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create simplified result with only essential information.

        Args:
            result: Full parsing result dictionary

        Returns:
            Simplified result dictionary
        """
        simplified_result = {
            "message_id": result.get("message_id", ""),
            "subject": result.get("subject", ""),
            "sender": result.get("sender", ""),
            "recipients": result.get("recipients", ""),
            "received_at": result.get("received_at", ""),
            "text_content": result.get("text_content", ""),
            "attachments": []
        }

        # Convert received_at to ISO format if it exists and has isoformat
        # method
        if simplified_result["received_at"]:
            if hasattr(simplified_result["received_at"], "isoformat"):
                simplified_result["received_at"] = (
                    simplified_result["received_at"].isoformat()
                )

        # Simplify attachments - only keep MD5 and basic info, no file paths
        for attachment in result.get("attachments", []):
            simplified_attachment = self._simplify_attachment(attachment)
            simplified_result["attachments"].append(simplified_attachment)

        return simplified_result

    def _simplify_attachment(
        self, attachment: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Simplify attachment information to essential fields only.

        Args:
            attachment: Full attachment dictionary

        Returns:
            Simplified attachment dictionary
        """
        return {
            "filename": attachment.get("filename", ""),
            "safe_filename": attachment.get("safe_filename", ""),
            "content_type": attachment.get("content_type", ""),
            "file_size": attachment.get("file_size", 0),
            "is_image": attachment.get("is_image", False)
        }

    def _validate_results(
        self, eml_file: Path, result: Dict[str, Any], validation_data: Dict
    ):
        """Validate parsing results against expected data"""
        self.stdout.write(f"\n🔍 Validating results...")

        # Get expected data for this file
        file_key = eml_file.name
        if file_key not in validation_data:
            warning_msg = f"⚠️  No validation data for {file_key}"
            self.stdout.write(self.style.WARNING(warning_msg))
            return

        expected = validation_data[file_key]
        validation_passed = True

        # Validate basic fields
        for field in ['subject', 'sender', 'recipients']:
            if field in expected:
                actual = result.get(field, '')
                expected_value = expected[field]
                if actual != expected_value:
                    error_msg = (
                        f"❌ {field.title()} mismatch: expected "
                        f"'{expected_value}', got '{actual}'"
                    )
                    self.stdout.write(self.style.ERROR(error_msg))
                    validation_passed = False
                else:
                    self.stdout.write(f"✅ {field.title()} matches")

        # Validate text content
        if 'text_content' in expected:
            expected_text_lines = expected['text_content']
            actual_text = result.get('text_content', '')

            # Normalize both texts
            expected_full_text = '\n'.join(expected_text_lines)
            normalized_actual = ' '.join(actual_text.split())
            normalized_expected = ' '.join(expected_full_text.split())

            if normalized_actual == normalized_expected:
                self.stdout.write("✅ Text content matches perfectly")
            else:
                self.stdout.write(self.style.ERROR("❌ Text content mismatch"))
                validation_passed = False

        # Validate attachments
        if 'attachments' in expected:
            expected_attachments = expected['attachments']
            actual_attachments = result.get('attachments', [])

            expected_count = expected_attachments.get('count', 0)
            actual_count = len(actual_attachments)

            if actual_count == expected_count:
                count_msg = f"✅ Attachment count matches ({actual_count})"
                self.stdout.write(count_msg)
            else:
                error_msg = (
                    f"❌ Attachment count mismatch: expected "
                    f"{expected_count}, got {actual_count}"
                )
                self.stdout.write(self.style.ERROR(error_msg))
                validation_passed = False

        if validation_passed:
            success_msg = "🎉 All validations passed!"
            self.stdout.write(self.style.SUCCESS(success_msg))
        else:
            error_msg = "💥 Some validations failed"
            self.stdout.write(self.style.ERROR(error_msg))

    def _load_validation_data(self, validation_file: str) -> Dict:
        """Load validation data from JSON file"""
        try:
            with open(validation_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            error_msg = f"Error loading validation file {validation_file}: {e}"
            raise CommandError(error_msg)

    def _print_header(self, count: int, source_type: str):
        """Print command header"""
        if not self.summary_only:
            self.stdout.write("=" * 80)
            self.stdout.write(
                self.style.SUCCESS("🔧 Unified Email Parser Command")
            )
            self.stdout.write(f"📧 Processing {count} {source_type}")
            self.stdout.write("=" * 80)
        else:
            summary_header = (
                f"📧 Processing {count} {source_type} (Summary Mode)"
            )
            self.stdout.write(summary_header)
            self.stdout.write("-" * 80)

    def _print_summary(self, success_count: int, total_count: int):
        """Print final summary"""
        self.stdout.write("=" * 80)
        self.stdout.write(f"📊 SUMMARY")
        self.stdout.write(f"   Processed: {success_count}/{total_count} files")

        if success_count == total_count:
            success_msg = "✅ All files processed successfully!"
            self.stdout.write(self.style.SUCCESS(success_msg))
        else:
            failed_count = total_count - success_count
            error_msg = f"❌ {failed_count} file(s) failed to process"
            self.stdout.write(self.style.ERROR(error_msg))

        self.stdout.write("=" * 80)
