import base64
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, Generator, Optional

import imaplib
import mailparser
from email_validator import validate_email, EmailNotValidError

logger = logging.getLogger(__name__)


class EmailClient:
    """
    Email client service for fetching emails from IMAP server.
    Using mail-parser library for robust email parsing.
    """
    IMAP_SSL_DEFAULT_PORT = 993
    IMAP_DEFAULT_PORT = 143
    SMTP_TO_IMAP_HOST_REPLACE = ('smtp.', 'imap.')
    DEFAULT_EMAIL_FOLDER = 'INBOX'
    SEARCH_CRITERIA_UNSEEN = 'UNSEEN'
    SEARCH_CRITERIA_FROM = 'FROM'
    SEARCH_CRITERIA_SUBJECT = 'SUBJECT'
    SEARCH_CRITERIA_SINCE = 'SINCE'
    SEARCH_CRITERIA_ALL = 'ALL'
    FILTER_PREFIX_UNREAD = 'unread'
    FILTER_PREFIX_FROM = 'from:'
    FILTER_PREFIX_SUBJECT = 'subject:'
    FILTER_PREFIX_SINCE = 'since:'
    IMAP_DATE_FORMAT = '%d-%b-%Y'
    EMAIL_ATTACHMENT_PREFIX = 'email_attachment_'
    IMAGE_CONTENT_TYPE_PREFIX = 'image/'

    def __init__(
        self,
        email_config: Dict,
        email_filter_config: Dict,
        attachment_storage_path: str = '/tmp/attachments'
    ):
        """
        Initialize email client with email and filter configurations.
        """
        self.email_config = email_config
        self.email_filter_config = email_filter_config
        self.attachment_storage_path = attachment_storage_path
        self._client = None
        self._imap_host = None
        self._imap_port = None
        self._use_ssl = None
        self._folder = None
        self._search_criteria = None

    @property
    def client(self):
        """
        Get or initialize IMAP client connection.
        """
        if self._client is None:
            self._client = self._connect_and_login()
        return self._client

    def _connect_and_login(self):
        """
        Internal method to connect and login to IMAP server.
        """
        try:
            logger.info(
                f"Connecting to IMAP server: "
                f"{self.imap_host}:{self.imap_port}"
            )
            client = (
                imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
                if self.use_ssl
                else imaplib.IMAP4(self.imap_host, self.imap_port)
            )
            client.login(
                self.email_config.get('username'),
                self.email_config.get('password')
            )
            logger.info("Successfully connected to IMAP server")
            return client
        except Exception as e:
            logger.error(
                f"Failed to connect to IMAP server: {e}"
            )
            return None

    def connect(self) -> bool:
        """
        Connect to IMAP server and login (for compatibility).
        """
        if self._client is None:
            self._client = self._connect_and_login()
        return self._client is not None

    def disconnect(self):
        """
        Disconnect from IMAP server.
        """
        if self._client:
            try:
                self._client.logout()
                logger.info("Disconnected from IMAP server")
            except Exception as e:
                logger.error(f"Error disconnecting from IMAP server: {e}")
            self._client = None

    @property
    def imap_host(self) -> str:
        """
        Get IMAP host from configuration.
        """
        if self._imap_host is None:
            self._imap_host = self.email_config.get('imap_host')
            if not self._imap_host:
                self._imap_host = self.email_config.get('host', '').replace(
                    *self.SMTP_TO_IMAP_HOST_REPLACE
                )
        return self._imap_host

    @property
    def imap_port(self) -> int:
        """
        Get IMAP port from configuration.
        """
        if self._imap_port is None:
            self._imap_port = self.email_config.get(
                'imap_ssl_port', self.IMAP_SSL_DEFAULT_PORT
            )
        return self._imap_port

    @property
    def use_ssl(self) -> bool:
        """
        Determine if SSL should be used.
        """
        if self._use_ssl is None:
            self._use_ssl = (
                self.imap_port == self.IMAP_SSL_DEFAULT_PORT or
                self.email_config.get('use_ssl', True)
            )
        return self._use_ssl

    @property
    def folder(self) -> str:
        """
        Get the email folder to scan.
        """
        if self._folder is None:
            self._folder = self.email_filter_config.get(
                'folder', self.DEFAULT_EMAIL_FOLDER
            )
        return self._folder

    @property
    def search_criteria(self) -> str:
        """
        Build IMAP search criteria based on filter configuration.
        """
        # Return immediately if already set (not None or empty)
        if self._search_criteria:
            return self._search_criteria

        filters = self.email_filter_config.get('filters', [])
        criteria = [
            c
            for f in filters
            for c in self._process_filter_item(f)
        ]
        max_age_days = self.email_filter_config.get('max_age_days')
        if max_age_days:
            since_date = self._get_since_date(max_age_days)
            criteria.append(
                f'{self.SEARCH_CRITERIA_SINCE} "{since_date}"'
            )
        self._search_criteria = (
            ' '.join(criteria) if criteria else self.SEARCH_CRITERIA_ALL
        )
        return self._search_criteria

    def _process_filter_item(self, filter_item: str) -> list:
        """
        Process individual filter item.
        """
        criteria = []
        if filter_item.startswith(self.FILTER_PREFIX_UNREAD):
            criteria.append(self.SEARCH_CRITERIA_UNSEEN)
        elif filter_item.startswith(self.FILTER_PREFIX_FROM):
            sender = filter_item.split(':', 1)[1]
            criteria.append(f'{self.SEARCH_CRITERIA_FROM} "{sender}"')
        elif filter_item.startswith(self.FILTER_PREFIX_SUBJECT):
            subject = filter_item.split(':', 1)[1]
            criteria.append(f'{self.SEARCH_CRITERIA_SUBJECT} "{subject}"')
        elif filter_item.startswith(self.FILTER_PREFIX_SINCE):
            date = filter_item.split(':', 1)[1]
            criteria.append(f'{self.SEARCH_CRITERIA_SINCE} "{date}"')
        return criteria

    def _get_since_date(self, max_age_days: int) -> str:
        """
        Get since date string for IMAP search.
        """
        since_date = (
            datetime.now() - timedelta(days=max_age_days)
        ).strftime(self.IMAP_DATE_FORMAT)
        return since_date

    def validate_email_address(self, email_address: str) -> bool:
        """
        Validate email address using email-validator.
        """
        try:
            validate_email(email_address)
            return True
        except EmailNotValidError:
            return False

    def _extract_email_body(self, mail, email_data: bytes) -> (str, str):
        """
        Robustly extract text and html content from a mailparser mail object.
        Handles compatibility for mailparser, MIME parts, and mail.mail['body'].
        """
        text_content = mail.body_plain or ''
        html_content = mail.body_html or ''
        # If both text and html content are empty, try to extract from parts
        if not (text_content or html_content) and \
           hasattr(mail, 'mail') and hasattr(mail.mail, 'parts'):
            for part in mail.mail.parts:
                ctype = part.get('content_type')
                payload = part.get('payload', b'')
                encoding = part.get('content_transfer_encoding', '').lower()
                # Handle text/plain
                if ctype == 'text/plain' and not text_content:
                    text_content = self._decode_payload(payload, encoding)
                # Handle text/html
                if ctype == 'text/html' and not html_content:
                    html_content = self._decode_payload(payload, encoding)
        # Fallback: try to get body from mail.mail dict
        if not text_content and isinstance(getattr(mail, 'mail', None), dict):
            text_content = mail.mail.get('body', '')
        return text_content, html_content

    def _decode_payload(self, payload, encoding) -> str:
        """
        Decode email payload with given encoding.
        """
        if encoding == 'base64':
            try:
                return base64.b64decode(payload).decode(
                    'utf-8', errors='ignore'
                )
            except Exception:
                return payload.decode('utf-8', errors='ignore')
        return payload.decode('utf-8', errors='ignore')

    def parse_email_with_mail_parser(
        self, email_data: bytes, message_id: str
    ) -> Optional[Dict]:
        """
        Parse email using mail-parser library.
        """
        try:
            mail = mailparser.parse_from_bytes(email_data)
            text_content, html_content = self._extract_email_body(mail, email_data)
            logger.debug(f"[Extracted Text] {text_content[:200]}")
            logger.debug(f"[Extracted HTML] {html_content[:200]}")
            raw_content = email_data.decode('utf-8', errors='ignore')
            attachments = self._process_attachments(mail)
            logger.debug(f"Found {len(attachments)} attachments")
            return {
                'message_id': message_id,
                'subject': mail.subject or '',
                'sender': mail.from_[0][1] if mail.from_ else '',
                'recipients': ', '.join([to[1] for to in mail.to]) if mail.to else '',
                'received_at': mail.date or datetime.now(),
                'raw_content': raw_content,
                'html_content': html_content,
                'text_content': text_content,
                'content': text_content or html_content or '',
                'attachments': attachments
            }
        except Exception as e:
            logger.error(f"Error parsing email message {message_id}: {e}")
            return None

    def _process_attachments(self, mail) -> list:
        """
        Process email attachments.
        """
        attachments = []
        for attachment in mail.attachments:
            try:
                attachment_data = self._process_single_attachment(attachment)
                if attachment_data:
                    attachments.append(attachment_data)
            except Exception as e:
                logger.error(
                    "Attachment error [%s]: %s",
                    getattr(attachment, 'filename', str(attachment)),
                    e
                )
                continue
        return attachments

    def _process_single_attachment(self, attachment) -> Optional[Dict]:
        """
        Process a single email attachment.
        """
        logger.debug(
            f"Processing attachment: type={type(attachment)}, "
            f"filename={getattr(attachment, 'filename', None)}"
        )

        try:
            # Extract attachment info based on type
            if isinstance(attachment, dict):
                # Handle dict type attachments (from mailparser)
                filename = attachment.get('filename', 'unknown')
                # Try different content type field names
                content_type = (
                    attachment.get('content-type') or
                    attachment.get('mail_content_type') or
                    'application/octet-stream'
                )
                payload = attachment.get('payload', '')
                binary = attachment.get('binary', False)

                # Decode content
                if payload and binary:
                    import base64
                    try:
                        content = base64.b64decode(payload)
                    except Exception as e:
                        logger.error(f"Failed to decode base64 payload: {e}")
                        content = payload.encode('utf-8', errors='ignore')
                else:
                    content = payload.encode('utf-8', errors='ignore')
            else:
                # Handle mailparser attachment objects
                filename = attachment.filename
                content_type = attachment.content_type
                content = attachment.content

            # Create storage directory
            os.makedirs(self.attachment_storage_path, exist_ok=True)
            logger.debug(f"Ensured attachment storage path exists: "
                         f"{self.attachment_storage_path}")

            # Generate unique filename and save file
            unique_id = str(uuid.uuid4())[:8]
            safe_filename = f"{unique_id}_{filename}"
            file_path = os.path.join(self.attachment_storage_path,
                                     safe_filename)

            logger.info(f"Saving attachment '{filename}' to '{file_path}'")
            logger.debug(f"Storage path: {self.attachment_storage_path}")
            logger.debug(f"Safe filename: {safe_filename}")
            logger.debug(f"Full file path: {file_path}")

            with open(file_path, 'wb') as f:
                f.write(content)
            logger.info(f"Attachment '{filename}' saved successfully, "
                        f"size={len(content)} bytes")

            # Determine if it's an image
            is_image = content_type.startswith(self.IMAGE_CONTENT_TYPE_PREFIX)
            logger.debug(f"Attachment '{filename}' content_type="
                         f"{content_type}, is_image={is_image}")

            return {
                'filename': filename,
                'content_type': content_type,
                'file_size': len(content),
                'file_path': file_path,
                'is_image': is_image
            }

        except Exception as e:
            filename = getattr(attachment, 'filename',
                               attachment.get('filename', str(attachment)))
            logger.error(f"Error processing attachment {filename}: {e}",
                         exc_info=True)
            return None

    def scan_emails(self) -> Generator[Dict, None, None]:
        """
        Scan emails from IMAP server using mail-parser.
        """
        if not self.connect():
            logger.error("Failed to connect to IMAP server")
            return
        try:
            logger.info(f"Selecting folder: {self.folder}")
            self.client.select(self.folder)
            logger.info(f"Search criteria: {self.search_criteria}")
            status, message_numbers = self.client.search(
                None, self.search_criteria
            )
            if status != 'OK':
                logger.error(f"Failed to search emails: {status}")
                return
            message_number_list = message_numbers[0].split()
            logger.info(f"Found {len(message_number_list)} emails to process")
            for message_number in message_number_list:
                try:
                    status, email_data = self.client.fetch(
                        message_number, '(RFC822)'
                    )
                    if status != 'OK':
                        logger.warning(
                            f"Failed to fetch email {message_number}: {status}"
                        )
                        continue
                    raw_email = email_data[0][1]
                    message_id = f"{self.folder}_{message_number.decode()}"
                    parsed_email = self.parse_email_with_mail_parser(
                        raw_email, message_id
                    )
                    if parsed_email:
                        yield parsed_email
                except Exception as e:
                    logger.error(f"Error processing email {message_number}: {e}")
                    continue
        except Exception as e:
            logger.error(f"Error scanning emails: {e}")
        finally:
            self.disconnect()

    def __enter__(self):
        """
        Context manager entry.
        """
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit.
        """
        self.disconnect()