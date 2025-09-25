"""
Unified Email Processor - Supports multiple email sources and parsers
Combines IMAP client, file monitoring, and different email parsers
"""

import os
import json
import shutil
import logging
from typing import Dict, Generator, Optional, Any, List, Union
from enum import Enum

from django.conf import settings

from .imap_client import IMAPClient
from .email_parser import EmailParser
from .email_flanker_parser import EmailFlankerParser

logger = logging.getLogger(__name__)


class EmailSource(Enum):
    """Email source types"""
    IMAP = "imap"
    FILE = "file"


class ParserType(Enum):
    """Email parser types"""
    LEGACY = "legacy"  # Original EmailParser
    FLANKER = "flanker"  # Enhanced EmailFlankerParser


class EmailProcessor:
    """
    Unified email processor supporting multiple sources and parsers.

    Features:
    - Multiple email sources: IMAP or file system
    - Multiple parsers: legacy EmailParser or enhanced EmailFlankerParser
    - Database integration for file-based processing
    - Flexible configuration through parameters
    """

    def __init__(
        self,
        source: Union[EmailSource, str] = EmailSource.IMAP,
        parser_type: Union[ParserType, str] = ParserType.FLANKER,
        email_config: Optional[Dict] = None,
        attachment_storage_path: str = '/tmp/attachments',
        file_config: Optional[Dict] = None
    ):
        """
        Initialize unified email processor.

        Args:
            source: Email source type - 'imap' or 'file' (default: 'imap')
            parser_type: Parser type - 'legacy' or 'flanker' (default: 'flanker')
            email_config: IMAP configuration (required for IMAP source)
            attachment_storage_path: Path for storing email attachments
            file_config: File system configuration (required for file source)
        """
        # Convert string parameters to enums
        if isinstance(source, str):
            self.source = EmailSource(source.lower())
        else:
            self.source = source

        if isinstance(parser_type, str):
            self.parser_type = ParserType(parser_type.lower())
        else:
            self.parser_type = parser_type

        self.attachment_storage_path = attachment_storage_path
        self.email_config = email_config or {}

        # Initialize parser based on type
        self._initialize_parser()

        # Initialize source-specific components
        self._initialize_source(file_config)

        logger.info(f"EmailProcessor initialized: source={self.source.value}, "
                   f"parser={self.parser_type.value}")

    def _initialize_parser(self):
        """Initialize email parser based on parser type"""
        if self.parser_type == ParserType.FLANKER:
            self.email_parser = EmailFlankerParser(self.attachment_storage_path)
            logger.info("Using EmailFlankerParser (enhanced)")
        else:
            self.email_parser = EmailParser(self.attachment_storage_path)
            logger.info("Using EmailParser (legacy)")

    def _initialize_source(self, file_config: Optional[Dict] = None):
        """Initialize email source components"""
        if self.source == EmailSource.IMAP:
            # Extract IMAP and filter configs from unified structure
            self.imap_config = self.email_config.get('imap_config', {})
            self.filter_config = self.email_config.get('filter_config', {})
            self.imap_client = IMAPClient(self.imap_config, self.filter_config)
            logger.info("Initialized IMAP client")

        elif self.source == EmailSource.FILE:
            # Initialize file system components
            self._initialize_file_system(file_config)
            logger.info("Initialized file system monitoring")
        else:
            raise ValueError(f"Unsupported email source: {self.source}")

    def _initialize_file_system(self, file_config: Optional[Dict] = None):
        """Initialize file system monitoring components"""
        # Use provided config or Django settings
        if file_config:
            self.base_dir = file_config.get('base_dir', '/tmp/emails')
            self.inbox_dir = file_config.get('inbox_dir',
                                           os.path.join(self.base_dir, 'inbox'))
            self.processing_dir = file_config.get('processing_dir',
                                                os.path.join(self.base_dir, 'processing'))
            self.failed_dir = file_config.get('failed_dir',
                                            os.path.join(self.base_dir, 'failed'))
            self.auto_assign_domain = file_config.get('auto_assign_domain',
                                                    'devify.local')
        else:
            # Use Django settings if available, otherwise use defaults
            try:
                self.base_dir = getattr(settings, 'EMAIL_BASE_DIR', '/tmp/emails')
                self.inbox_dir = getattr(settings, 'EMAIL_INBOX_DIR',
                                       os.path.join(self.base_dir, 'inbox'))
                self.processing_dir = getattr(settings, 'EMAIL_PROCESSING_DIR',
                                            os.path.join(self.base_dir, 'processing'))
                self.failed_dir = getattr(settings, 'EMAIL_FAILED_DIR',
                                        os.path.join(self.base_dir, 'failed'))
                self.auto_assign_domain = getattr(settings, 'AUTO_ASSIGN_EMAIL_DOMAIN',
                                                'devify.local')
            except Exception:
                # Django settings not available, use defaults
                self.base_dir = '/tmp/emails'
                self.inbox_dir = os.path.join(self.base_dir, 'inbox')
                self.processing_dir = os.path.join(self.base_dir, 'processing')
                self.failed_dir = os.path.join(self.base_dir, 'failed')
                self.auto_assign_domain = 'devify.local'

        # Ensure directories exist
        try:
            for directory in [self.inbox_dir, self.processing_dir, self.failed_dir]:
                os.makedirs(directory, exist_ok=True)
        except PermissionError as e:
            logger.warning(f"Permission denied creating directories: {e}")
            # Use temp directories instead
            import tempfile
            temp_base = tempfile.mkdtemp(prefix='email_processor_')
            self.base_dir = temp_base
            self.inbox_dir = os.path.join(temp_base, 'inbox')
            self.processing_dir = os.path.join(temp_base, 'processing')
            self.failed_dir = os.path.join(temp_base, 'failed')
            for directory in [self.inbox_dir, self.processing_dir, self.failed_dir]:
                os.makedirs(directory, exist_ok=True)

    def process_emails(self) -> Generator[Dict, None, None]:
        """
        Process emails based on configured source.
        Yields parsed email data dictionaries.

        Returns:
            Generator of parsed email data dictionaries
        """
        if self.source == EmailSource.IMAP:
            yield from self._process_imap_emails()
        elif self.source == EmailSource.FILE:
            yield from self._process_file_emails()
        else:
            raise ValueError(f"Unsupported email source: {self.source}")

    def _process_imap_emails(self) -> Generator[Dict, None, None]:
        """Process emails from IMAP server"""
        try:
            logger.info("Starting email processing from IMAP server")

            # Use IMAP client to get raw email data
            for raw_email_data in self.imap_client.scan_emails():
                # Parse email data using email parser
                parsed_email = self.email_parser.parse_from_bytes(
                    raw_email_data)

                if parsed_email:
                    yield parsed_email
                else:
                    logger.warning("Failed to parse email, skipping")

        except Exception as e:
            logger.error(f"Error in IMAP email processing: {e}")
            raise

    def _process_file_emails(self) -> Generator[Dict, None, None]:
        """Process emails from file system"""
        try:
            logger.info("Starting email processing from file system")

            # Scan for emails in inbox
            uuids = self.scan_inbox()
            if not uuids:
                logger.info("No emails found in inbox")
                return

            logger.info(f"Found {len(uuids)} emails to process")

            for uuid in uuids:
                try:
                    # Load email data
                    email_data = self.load_email_data(uuid)
                    if not email_data:
                        continue

                    # Parse email content
                    parsed_email = self.email_parser.parse_from_string(
                        email_data['raw_content'])

                    if parsed_email:
                        # Add metadata to parsed result
                        parsed_email['uuid'] = uuid
                        parsed_email['metadata'] = email_data['metadata']
                        yield parsed_email
                    else:
                        logger.warning(f"Failed to parse email {uuid}")

                except Exception as e:
                    logger.error(f"Error processing email {uuid}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error in file email processing: {e}")
            raise

    def parse_email_from_bytes(self, email_data: bytes) -> Optional[Dict]:
        """
        Parse email from raw bytes data.

        Args:
            email_data: Raw email data as bytes

        Returns:
            Parsed email data dictionary or None if parsing fails
        """
        return self.email_parser.parse_from_bytes(email_data)

    def parse_email_from_file(self, file_path: str) -> Optional[Dict]:
        """
        Parse email from file.

        Args:
            file_path: Path to email file

        Returns:
            Parsed email data dictionary or None if parsing fails
        """
        return self.email_parser.parse_from_file(file_path)

    def parse_email_from_string(self, raw_content: str) -> Optional[Dict]:
        """
        Parse email from string content.

        Args:
            raw_content: Raw email content as string

        Returns:
            Parsed email data dictionary or None if parsing fails
        """
        return self.email_parser.parse_from_string(raw_content)

    def validate_email_address(self, email_address: str) -> bool:
        """
        Validate email address using email-validator.

        Args:
            email_address: Email address to validate

        Returns:
            True if email address is valid, False otherwise
        """
        return self.email_parser.validate_email_address(email_address)

    # File system methods (for FILE source)
    def scan_inbox(self) -> List[str]:
        """
        Scan inbox directory for new emails.
        Returns list of email UUIDs to process.
        """
        try:
            if not os.path.exists(self.inbox_dir):
                logger.warning(f"Inbox directory does not exist: {self.inbox_dir}")
                return []

            # Find all .meta files in inbox
            meta_files = [f for f in os.listdir(self.inbox_dir)
                         if f.endswith('.meta')]

            if not meta_files:
                return []

            # Extract UUIDs and verify both files exist
            valid_uuids = []
            for meta_file in meta_files:
                uuid = meta_file.replace('.meta', '')
                eml_file = os.path.join(self.inbox_dir, f'{uuid}.eml')

                if os.path.exists(eml_file):
                    valid_uuids.append(uuid)
                else:
                    logger.warning(f"Missing .eml file for {uuid}")

            return valid_uuids

        except Exception as e:
            logger.error(f"Error scanning inbox: {e}")
            return []

    def load_email_data(self, uuid: str) -> Optional[Dict[str, Any]]:
        """
        Load email data from inbox files.
        """
        try:
            meta_file = os.path.join(self.inbox_dir, f'{uuid}.meta')
            eml_file = os.path.join(self.inbox_dir, f'{uuid}.eml')

            # Verify files exist
            if not os.path.exists(meta_file):
                logger.error(f"Missing meta file for {uuid}: {meta_file}")
                return None
            if not os.path.exists(eml_file):
                logger.error(f"Missing eml file for {uuid}: {eml_file}")
                return None

            # Load metadata
            with open(meta_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            # Load raw email content
            with open(eml_file, 'r', encoding='utf-8') as f:
                raw_content = f.read()

            return {
                'metadata': metadata,
                'raw_content': raw_content,
                'eml_file': eml_file,
                'meta_file': meta_file
            }

        except Exception as e:
            logger.error(f"Error loading email {uuid}: {e}")
            return None

    def _move_files_safely(self, uuid: str, from_dir: str, to_dir: str) -> bool:
        """
        Helper method to safely move email files between directories.
        """
        try:
            src_eml = os.path.join(from_dir, f'{uuid}.eml')
            src_meta = os.path.join(from_dir, f'{uuid}.meta')
            dst_eml = os.path.join(to_dir, f'{uuid}.eml')
            dst_meta = os.path.join(to_dir, f'{uuid}.meta')

            files_moved = 0

            # Move .eml file if exists
            if os.path.exists(src_eml):
                logger.info(f"Moving eml file from {src_eml} to {dst_eml}")
                shutil.move(src_eml, dst_eml)
                files_moved += 1
            else:
                logger.warning(f"Missing eml file for {uuid}: {src_eml}")

            # Move .meta file if exists
            if os.path.exists(src_meta):
                logger.info(f"Moving meta file from {src_meta} to {dst_meta}")
                shutil.move(src_meta, dst_meta)
                files_moved += 1
            else:
                logger.warning(f"Missing meta file for {uuid}: {src_meta}")

            return files_moved > 0

        except Exception as e:
            logger.error(f"Error moving files for {uuid}: {e}")
            return False

    def _delete_email_files(self, uuid: str, from_dir: str) -> bool:
        """
        Helper method to safely delete email files.
        """
        try:
            eml_file = os.path.join(from_dir, f'{uuid}.eml')
            meta_file = os.path.join(from_dir, f'{uuid}.meta')

            files_deleted = 0

            # Delete .eml file if exists
            if os.path.exists(eml_file):
                os.remove(eml_file)
                files_deleted += 1
                logger.debug(f"Deleted eml file: {eml_file}")
            else:
                logger.warning(f"Missing eml file for {uuid}: {eml_file}")

            # Delete .meta file if exists
            if os.path.exists(meta_file):
                os.remove(meta_file)
                files_deleted += 1
                logger.debug(f"Deleted meta file: {meta_file}")
            else:
                logger.warning(f"Missing meta file for {uuid}: {meta_file}")

            logger.info(f"Cleaned up {files_deleted} files for {uuid}")
            return files_deleted > 0

        except Exception as e:
            logger.error(f"Error deleting files for {uuid}: {e}")
            return False

    def move_to_processing(self, uuid: str) -> bool:
        """
        Move email files from inbox to processing directory.
        """
        return self._move_files_safely(uuid, self.inbox_dir, self.processing_dir)

    def move_to_completed(self, uuid: str, success: bool = True) -> bool:
        """
        Complete email processing by cleaning up files.

        Args:
            uuid: Email UUID
            success: If True, delete files; if False, move to failed directory
        """
        if success:
            # Successfully processed - delete the files
            return self._delete_email_files(uuid, self.processing_dir)
        else:
            # Failed processing - move to failed directory for debugging
            return self._move_files_safely(uuid, self.processing_dir, self.failed_dir)

    # IMAP methods (for IMAP source)
    def connect(self) -> bool:
        """
        Connect to IMAP server (for compatibility with existing code).

        Returns:
            True if connection successful, False otherwise
        """
        if self.source == EmailSource.IMAP:
            return self.imap_client.connect()
        else:
            logger.warning("Connect method only available for IMAP source")
            return False

    def disconnect(self):
        """
        Disconnect from IMAP server (for compatibility with existing code).
        """
        if self.source == EmailSource.IMAP:
            self.imap_client.disconnect()
        else:
            logger.warning("Disconnect method only available for IMAP source")

    def __enter__(self):
        """
        Context manager entry.
        """
        if self.source == EmailSource.IMAP:
            self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit.
        """
        if self.source == EmailSource.IMAP:
            self.disconnect()
