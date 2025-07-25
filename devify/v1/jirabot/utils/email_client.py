import base64
import hashlib
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, Generator, Optional

import imaplib
import mailparser
from email_validator import validate_email, EmailNotValidError
from django.utils import timezone

# Disable mailparser debug logs in this file
logging.getLogger('mailparser').setLevel(logging.WARNING)
logging.getLogger('mailparser.mailparser').setLevel(logging.WARNING)
logging.getLogger('mailparser.utils').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


class EmailClient:
    """
    Email client service for fetching emails from IMAP server.
    Using mail-parser library for robust email parsing.
    """
    IMAP_SSL_DEFAULT_PORT = 993
    IMAP_DEFAULT_PORT = 143
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
        self._imap_client = None

        self._search_criteria = None

    def _generate_stable_message_id(self, mail, received_at) -> str:
        """
        Generate a stable unique message_id using key email fields.
        """
        subject = mail.subject or ''
        sender = mail.from_[0][1] if mail.from_ else ''
        recipients = ','.join(
            to[1] for to in mail.to
        ) if mail.to else ''
        base = f"{subject}|{sender}|{recipients}|{received_at.isoformat()}"
        msg_hash = hashlib.sha256(
            base.encode('utf-8')
        ).hexdigest()[:16]
        return f"email_{msg_hash}"

    @property
    def imap_client(self):
        """
        Get or initialize IMAP client connection.
        """
        if self._imap_client is None:
            self._imap_client = self._connect_and_login_imap()

        return self._imap_client

    def _connect_and_login_imap(self):
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
                f"Failed to connect to IMAP server due to: {e}"
            )
            raise

    def connect(self) -> bool:
        """
        Connect to IMAP server and login (for compatibility).
        """
        if self._imap_client is None:
            self._imap_client = self._connect_and_login_imap()
        return self._imap_client is not None

    def disconnect(self):
        """
        Disconnect from IMAP server.
        """
        if self._imap_client:
            try:
                self._imap_client.logout()
                logger.info("Disconnected from IMAP server")
            except Exception as e:
                logger.error(f"Error disconnecting from IMAP server: {e}")
            self._imap_client = None

    @property
    def imap_host(self) -> str:
        """
        Return IMAP host from configuration directly.
        """
        return self.email_config.get('imap_host')

    @property
    def imap_port(self) -> int:
        """
        Get IMAP port from configuration.
        """
        return self.email_config.get(
            'imap_ssl_port', self.IMAP_SSL_DEFAULT_PORT
        )

    @property
    def use_ssl(self) -> bool:
        """
        Determine if SSL should be used.
        """
        return (
            self.imap_port == self.IMAP_SSL_DEFAULT_PORT or
            self.email_config.get('use_ssl', True)
        )

    @property
    def folder(self) -> str:
        """
        Get the email folder to scan.
        """
        return self.email_filter_config.get(
            'folder', self.DEFAULT_EMAIL_FOLDER
        )

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

        # Priority: use 'since' from config, then 'max_age_days'
        since_date = self.email_filter_config.get('since')
        if since_date:
            criteria.append(
                f'{self.SEARCH_CRITERIA_SINCE} "{since_date}"'
            )
        else:
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
        self, email_data: bytes
    ) -> Optional[Dict]:
        """
        Parse email using mail-parser library.
        """
        # First stage: parse email data
        try:
            mail = mailparser.parse_from_bytes(email_data)
        except Exception as e:
            preview = email_data[:100].decode('utf-8', errors='ignore')
            logger.error(
                f"Failed to parse email data - Error: {e}, Preview: {preview}"
            )
            return None

        # Second stage: process parsed email
        try:
            text_content, html_content = self._extract_email_body(
                mail, email_data)
            raw_content = email_data.decode('utf-8', errors='ignore')
            attachments = self._process_attachments(mail)
            # Generate stable message_id based on email content
            received_at = mail.date or timezone.now()
            # Ensure received_at has timezone info
            if received_at and timezone.is_naive(received_at):
                received_at = timezone.make_aware(received_at)
            stable_message_id = self._generate_stable_message_id(
                mail, received_at)
            recipients = ', '.join(to[1] for to in mail.to) if mail.to else ''

            return {
                'message_id': stable_message_id,
                'subject': mail.subject or '',
                'sender': mail.from_[0][1] if mail.from_ else '',
                'recipients': recipients,
                'received_at': received_at,
                'raw_content': raw_content,
                'html_content': html_content,
                'text_content': text_content,
                'content': text_content or html_content or '',
                'attachments': attachments
            }
        except Exception as e:
            subject = (
                getattr(mail, 'subject', 'Unknown Subject')
                or 'Unknown Subject'
            )
            sender = 'Unknown Sender'
            try:
                if hasattr(mail, 'from_') and mail.from_:
                    sender = mail.from_[0][1]
            except (IndexError, AttributeError):
                pass
            logger.error(
                f"Error processing parsed email - Subject: {subject}, "
                f"Sender: {sender}, Error: {e}"
            )
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
        try:
            if isinstance(attachment, dict):
                filename = attachment.get('filename', 'unknown')
                content_type = (
                    attachment.get('content-type') or
                    attachment.get('mail_content_type') or
                    'application/octet-stream'
                )
                payload = attachment.get('payload', '')
                binary = attachment.get('binary', False)
                if payload and binary:
                    try:
                        content = base64.b64decode(payload)
                    except Exception as e:
                        logger.error(
                            f"Failed to decode base64 payload: {e}"
                        )
                        content = payload.encode('utf-8', errors='ignore')
                else:
                    content = payload.encode('utf-8', errors='ignore')
            else:
                filename = attachment.filename
                content_type = attachment.content_type
                content = attachment.content
            os.makedirs(self.attachment_storage_path, exist_ok=True)
            unique_id = str(uuid.uuid4())[:8]
            safe_filename = f"{unique_id}_{filename}"
            file_path = os.path.join(
                self.attachment_storage_path, safe_filename)
            logger.info(
                f"Saving attachment '{filename}' to '{file_path}'"
            )
            with open(file_path, 'wb') as f:
                f.write(content)
            logger.info(
                f"Attachment '{filename}' saved successfully, "
                f"size={len(content)} bytes"
            )
            is_image = content_type.startswith(self.IMAGE_CONTENT_TYPE_PREFIX)
            return {
                'filename': filename,
                'content_type': content_type,
                'file_size': len(content),
                'file_path': file_path,
                'is_image': is_image
            }
        except Exception as e:
            filename = getattr(
                attachment, 'filename',
                attachment.get('filename', str(attachment))
            )
            logger.error(
                f"Error processing attachment {filename}: {e}",
                exc_info=True
            )
            return None

    def scan_emails(self) -> Generator[Dict, None, None]:
        """
        Scan emails from IMAP server using mail-parser.
        """
        try:
            logger.info(f"Search email from folder: {self.folder}")
            self.imap_client.select(self.folder)
            logger.info(f"Search criteria: {self.search_criteria}")
            status, message_numbers = self.imap_client.search(
                None, self.search_criteria
            )
            if status != 'OK':
                logger.error(f"Failed to search emails: {status}")
                return
            message_number_list = message_numbers[0].split()
            logger.info(
                f"Found {len(message_number_list)} emails to process"
            )
            for message_number in message_number_list:
                try:
                    status, email_data = self.imap_client.fetch(
                        message_number, '(RFC822)'
                    )
                    if status != 'OK':
                        logger.warning(
                            f"Failed to fetch email {message_number}: {status}"
                        )
                        continue
                    raw_email = email_data[0][1]
                    parsed_email = self.parse_email_with_mail_parser(
                        raw_email
                    )
                    if parsed_email:
                        yield parsed_email
                except Exception as e:
                    logger.error(
                        f"Error processing email {message_number}: {e}"
                    )
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