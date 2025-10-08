"""
Unified Email Processor - Supports multiple email sources and parsers

Combines IMAP client, file monitoring, and different email parsers.

Why use yield (Generator) instead of returning a list?
=====================================================
1. Memory Efficiency: Processes emails one at a time instead of loading
   all emails into memory simultaneously. This is crucial when handling
   large volumes of emails (hundreds or thousands).

2. Stream Processing: Allows immediate processing and saving of each
   email to database, reducing memory footprint and improving system
   stability.

3. Scalability: As email volume grows, the system remains stable without
   memory overflow issues.

4. Real-time Processing: Enables immediate feedback and error handling
   for each individual email.

This design is especially important for Haraka email processing where
large batches of emails may be present in the inbox directory.
"""

import json
import logging
import os
import shutil
from enum import Enum
from typing import Any, Dict, Generator, List, Optional, Union

from django.conf import settings

from .clients.imap import IMAPClient
from .parsers.enhanced import EmailFlankerParser
from .parsers.legacy import EmailParser

logger = logging.getLogger(__name__)


class EmailSource(Enum):
    """Email source types"""
    IMAP = "imap"
    FILE = "file"


class ParserType(Enum):
    """Email parser types"""
    LEGACY = "legacy"
    FLANKER = "flanker"


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
        attachment_dir: str = settings.TMP_EMAIL_ATTACHMENT_DIR,
        file_config: Optional[Dict] = None
    ):
        """
        Initialize unified email processor.

        Args:
            source: Email source type - 'imap' or 'file'
                   (default: 'imap')
            parser_type: Parser type - 'legacy' or 'flanker'
                        (default: 'flanker')
            email_config: IMAP configuration (required for IMAP source)
            attachment_dir: Directory for storing email attachments
            file_config: File system configuration (required for file
                       source)
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

        self.attachment_dir = attachment_dir
        self.email_config = email_config or {}

        # Initialize parser based on type
        self._init_parser()

        # Initialize source-specific components
        self._init_source(file_config)

        logger.info(
            f"EmailProcessor initialized: source={self.source.value}, "
            f"parser={self.parser_type.value}"
        )

    def _init_parser(self):
        """Initialize email parser based on parser type"""
        if self.parser_type == ParserType.FLANKER:
            self.email_parser = EmailFlankerParser(
                self.attachment_dir)
            logger.info("Using EmailFlankerParser (enhanced)")
        else:
            self.email_parser = EmailParser(self.attachment_dir)
            logger.info("Using EmailParser (legacy)")

    def _init_source(self, file_config: Optional[Dict] = None):
        """Initialize email source components"""
        if self.source == EmailSource.IMAP:
            # Extract IMAP and filter configs from unified structure
            self.imap_config = self.email_config.get('imap_config', {})
            self.filter_config = self.email_config.get(
                'filter_config', {}
            )
            self.imap_client = IMAPClient(self.imap_config,
                                        self.filter_config)
            logger.info("Initialized IMAP client")

        elif self.source == EmailSource.FILE:
            # Initialize file system components
            self._init_file_system()
            logger.info("Initialized file system monitoring")
        else:
            raise ValueError(f"Unsupported email source: {self.source}")

    def _init_file_system(self):
        """Initialize file system monitoring components"""
        # Use Django settings for all configuration
        self.base_dir = settings.HARAKA_EMAIL_BASE_DIR
        self.inbox_dir = os.path.join(self.base_dir, "inbox")
        self.processed_dir = os.path.join(self.base_dir, "processed")
        self.failed_dir = os.path.join(self.base_dir, "failed")
        self.auto_assign_domain = settings.AUTO_ASSIGN_EMAIL_DOMAIN

        # Ensure directories exist
        dirs = [self.inbox_dir, self.processed_dir, self.failed_dir]
        for directory in dirs:
            os.makedirs(directory, exist_ok=True)

    def process_emails(self) -> Generator[Dict, None, None]:
        """
        Process emails based on configured source.
        Yields parsed email data dictionaries.

        Returns:
            Generator of parsed email data dictionaries
        """
        if self.source == EmailSource.IMAP:
            yield from self._process_imap()
        elif self.source == EmailSource.FILE:
            yield from self._process_file()
        else:
            raise ValueError(f"Unsupported email source: {self.source}")

    def _process_imap(self) -> Generator[Dict, None, None]:
        """
        Process emails from IMAP server.

        Uses yield to process emails one at a time, avoiding memory
        issues when dealing with large email volumes from IMAP servers.
        """
        try:
            logger.info("Starting email processing from IMAP server")

            # Use IMAP client to get raw email data
            for raw_email_data in self.imap_client.scan_emails():
                # Parse email data using email parser
                parsed_email = self.email_parser.parse_from_bytes(
                    raw_email_data)

                if parsed_email:
                    # Yield immediately to avoid accumulating all emails
                    # in memory
                    yield parsed_email
                else:
                    logger.warning("Failed to parse email, skipping")

        except Exception as e:
            logger.error(f"Error in IMAP email processing: {e}")
            raise

    def _process_file(self) -> Generator[Dict, None, None]:
        """
        Process emails from file system.

        Uses yield to process emails one at a time, which is especially
        important for Haraka email processing where large batches of
        emails
        may be present in the inbox directory.
        """
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

                        # Override recipients with meta file data
                        # (more reliable)
                        if 'to' in email_data['metadata']:
                            meta_recipients = email_data['metadata'][
                                'to'
                            ]
                            if isinstance(meta_recipients, list):
                                parsed_email['recipients'] = (
                                    meta_recipients
                                )
                            elif isinstance(meta_recipients, str):
                                parsed_email['recipients'] = [
                                    meta_recipients
                                ]

                        # Move files to processed directory after
                        # successful parsing
                        self.move_to_processed(uuid)

                        # Yield immediately to avoid accumulating all
                        # emails
                    # in memory
                        yield parsed_email
                    else:
                        logger.warning(f"Failed to parse email {uuid}")
                        # Move failed emails to failed directory
                        self.move_to_failed(uuid)

                except Exception as e:
                    logger.error(f"Error processing email {uuid}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error in file email processing: {e}")
            raise

    def parse_from_bytes(self, email_data: bytes) -> Optional[Dict]:
        """
        Parse email from raw bytes data.

        Args:
            email_data: Raw email data as bytes

        Returns:
            Parsed email data dictionary or None if parsing fails
        """
        return self.email_parser.parse_from_bytes(email_data)

    def parse_from_file(self, file_path: str) -> Optional[Dict]:
        """
        Parse email from file.

        Args:
            file_path: Path to email file

        Returns:
            Parsed email data dictionary or None if parsing fails
        """
        return self.email_parser.parse_from_file(file_path)

    def parse_from_string(self, raw_content: str) -> Optional[Dict]:
        """
        Parse email from string content.

        Args:
            raw_content: Raw email content as string

        Returns:
            Parsed email data dictionary or None if parsing fails
        """
        return self.email_parser.parse_from_string(raw_content)

    def validate_email(self, email_address: str) -> bool:
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
                logger.warning(f"Inbox directory does not exist: "
                             f"{self.inbox_dir}")
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
                logger.error(
                    f"Missing meta file for {uuid}: {meta_file}"
                )
                return None
            if not os.path.exists(eml_file):
                logger.error(
                    f"Missing eml file for {uuid}: {eml_file}"
                )
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

    def _move_files_safely(
        self, uuid: str, from_dir: str, to_dir: str
    ) -> bool:
        """
        Safely move email files between directories with atomic operations.

        This method ensures that email files (.eml and .meta) are moved
        atomically and safely between directories. It handles missing files
        gracefully and provides detailed logging for debugging.

        Args:
            uuid: Email UUID for file identification
            from_dir: Source directory path
            to_dir: Destination directory path

        Returns:
            True if at least one file was moved successfully, False otherwise
        """
        try:
            # Ensure destination directory exists
            os.makedirs(to_dir, exist_ok=True)

            src_eml = os.path.join(from_dir, f'{uuid}.eml')
            src_meta = os.path.join(from_dir, f'{uuid}.meta')
            dst_eml = os.path.join(to_dir, f'{uuid}.eml')
            dst_meta = os.path.join(to_dir, f'{uuid}.meta')

            files_moved = 0
            errors = []

            # Move .eml file if exists
            if os.path.exists(src_eml):
                try:
                    logger.debug(
                        f"Moving eml file from {src_eml} to {dst_eml}"
                    )
                    shutil.move(src_eml, dst_eml)
                    files_moved += 1
                    logger.debug(f"Successfully moved eml file for {uuid}")
                except Exception as e:
                    error_msg = f"Failed to move eml file for {uuid}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            else:
                logger.warning(
                    f"Missing eml file for {uuid}: {src_eml}"
                )

            # Move .meta file if exists
            if os.path.exists(src_meta):
                try:
                    logger.debug(
                        f"Moving meta file from {src_meta} to {dst_meta}"
                    )
                    shutil.move(src_meta, dst_meta)
                    files_moved += 1
                    logger.debug(f"Successfully moved meta file for {uuid}")
                except Exception as e:
                    error_msg = f"Failed to move meta file for {uuid}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            else:
                logger.warning(
                    f"Missing meta file for {uuid}: {src_meta}"
                )

            # Log summary
            if files_moved > 0:
                logger.info(
                    f"Successfully moved {files_moved} files for {uuid} "
                    f"from {from_dir} to {to_dir}"
                )
            else:
                logger.warning(
                    f"No files were moved for {uuid} from {from_dir} to "
                    f"{to_dir}"
                )

            return files_moved > 0

        except Exception as e:
            logger.error(f"Error moving files for {uuid}: {e}")
            return False

    def _delete_files(self, uuid: str, from_dir: str) -> bool:
        """
        Safely delete email files from specified directory.

        This method ensures that email files (.eml and .meta) are deleted
        safely with proper error handling and logging.

        Args:
            uuid: Email UUID for file identification
            from_dir: Directory path containing files to delete

        Returns:
            True if at least one file was deleted successfully, False otherwise
        """
        try:
            eml_file = os.path.join(from_dir, f'{uuid}.eml')
            meta_file = os.path.join(from_dir, f'{uuid}.meta')

            files_deleted = 0
            errors = []

            # Delete .eml file if exists
            if os.path.exists(eml_file):
                try:
                    os.remove(eml_file)
                    files_deleted += 1
                    logger.debug(f"Successfully deleted eml file: {eml_file}")
                except Exception as e:
                    error_msg = f"Failed to delete eml file for {uuid}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            else:
                logger.debug(f"Eml file not found for {uuid}: {eml_file}")

            # Delete .meta file if exists
            if os.path.exists(meta_file):
                try:
                    os.remove(meta_file)
                    files_deleted += 1
                    logger.debug(f"Successfully deleted meta file: {meta_file}")
                except Exception as e:
                    error_msg = f"Failed to delete meta file for {uuid}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            else:
                logger.debug(f"Meta file not found for {uuid}: {meta_file}")

            # Log summary
            if files_deleted > 0:
                logger.info(
                    f"Successfully deleted {files_deleted} files for {uuid} "
                    f"from {from_dir}"
                )
            else:
                logger.warning(
                    f"No files were deleted for {uuid} from {from_dir}"
                )

            return files_deleted > 0

        except Exception as e:
            logger.error(f"Error deleting files for {uuid}: {e}")
            return False

    def move_to_processed(self, uuid: str) -> bool:
        """
        Move email files from inbox to processed directory.
        """
        success = self._move_files_safely(uuid, self.inbox_dir,
                                          self.processed_dir)
        if success:
            logger.info(f"Moved email {uuid} to processed directory")
        else:
            logger.warning(f"Failed to move email {uuid} to "
                           f"processed directory")
        return success

    def move_to_failed(self, uuid: str) -> bool:
        """
        Move email files from inbox to failed directory.
        """
        success = self._move_files_safely(uuid, self.inbox_dir,
                                          self.failed_dir)
        if success:
            logger.info(f"Moved failed email {uuid} to failed directory")
        else:
            logger.warning(
                f"Failed to move email {uuid} to failed directory"
            )
        return success

    def delete_from_processed(self, uuid: str) -> bool:
        """
        Delete email files from processed directory after successful
        processing.
        """
        return self._delete_files(uuid, self.processed_dir)

    def delete_from_failed(self, uuid: str) -> bool:
        """
        Delete email files from failed directory after cleanup.
        """
        return self._delete_files(uuid, self.failed_dir)

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
            logger.warning(
                "Connect method only available for IMAP source"
            )
            return False

    def disconnect(self):
        """
        Disconnect from IMAP server (for compatibility with existing
        code).
        """
        if self.source == EmailSource.IMAP:
            self.imap_client.disconnect()
        else:
            logger.warning(
                "Disconnect method only available for IMAP source"
            )

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
