"""
IMAP Client for connecting to and fetching emails from IMAP servers

Pure IMAP client without email parsing logic
"""

import imaplib
import logging
from typing import Dict, Generator, Optional

logger = logging.getLogger(__name__)


class IMAPClient:
    """
    Pure IMAP client for connecting to and fetching emails from IMAP servers.
    Handles only connection management and email retrieval, no parsing.
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

    def __init__(
        self,
        imap_config: Dict,
        filter_config: Dict,
        user_context: str = None
    ):
        """
        Initialize IMAP client with configuration.

        Args:
            imap_config: IMAP connection configuration
            filter_config: Email filtering configuration
            user_context: User context for logging (e.g., "user@example.com"
                         or "User ID: 123")
        """
        self.imap_config = imap_config
        self.filter_config = filter_config
        self.user_context = user_context or "Unknown user"
        self._imap_client = None
        self._search_criteria = None

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
        # Validate required configuration before attempting connection
        username = self.imap_config.get('username')
        password = self.imap_config.get('password')

        if not self.imap_host:
            error_msg = (
                f"[{self.user_context}] IMAP configuration error: "
                f"'imap_host' is missing or empty. "
                f"Please configure your IMAP server address in Settings."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        if not username:
            error_msg = (
                f"[{self.user_context}] IMAP configuration error: "
                f"'username' is missing or empty. "
                f"Please configure your IMAP username in Settings."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        if not password:
            error_msg = (
                f"[{self.user_context}] IMAP configuration error: "
                f"'password' is missing or empty. "
                f"Please configure your IMAP password in Settings."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        try:
            logger.info(
                f"[{self.user_context}] Connecting to IMAP server: "
                f"{self.imap_host}:{self.imap_port} "
                f"(SSL: {self.use_ssl})"
            )
            client = (
                imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
                if self.use_ssl
                else imaplib.IMAP4(self.imap_host, self.imap_port)
            )

            logger.info(f"Attempting login as: {username}")
            client.login(username, password)

            logger.info(
                f"[{self.user_context}] Successfully connected to IMAP server: "
                f"{self.imap_host}:{self.imap_port}"
            )
            return client

        except imaplib.IMAP4.error as e:
            error_msg = (
                f"[{self.user_context}] IMAP authentication failed for "
                f"{username}@{self.imap_host}: {e}\n"
                f"Possible causes:\n"
                f"  - Wrong username or password\n"
                f"  - Account locked or disabled\n"
                f"  - Two-factor authentication required\n"
                f"  - App-specific password needed"
            )
            logger.error(error_msg)
            raise ValueError(error_msg) from e

        except (ConnectionRefusedError, OSError) as e:
            error_msg = (
                f"[{self.user_context}] Cannot connect to IMAP server "
                f"{self.imap_host}:{self.imap_port}: {e}\n"
                f"Possible causes:\n"
                f"  - Wrong server address or port\n"
                f"  - Server is down or unreachable\n"
                f"  - Firewall blocking connection\n"
                f"  - SSL/TLS configuration mismatch (current: SSL={self.use_ssl})"
            )
            logger.error(error_msg)
            raise ConnectionError(error_msg) from e

        except Exception as e:
            error_msg = (
                f"[{self.user_context}] Unexpected error connecting to IMAP "
                f"server {self.imap_host}:{self.imap_port}: "
                f"{type(e).__name__}: {e}"
            )
            logger.error(error_msg)
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
                logger.error(
                    f"Error disconnecting from IMAP server: {e}"
                )
            self._imap_client = None

    @property
    def imap_host(self) -> str:
        """
        Return IMAP host from configuration directly.
        """
        return self.imap_config.get('imap_host')

    @property
    def imap_port(self) -> int:
        """
        Get IMAP port from configuration.
        """
        return self.imap_config.get(
            'imap_ssl_port', self.IMAP_SSL_DEFAULT_PORT
        )

    @property
    def use_ssl(self) -> bool:
        """
        Determine if SSL should be used.
        """
        return (
            self.imap_port == self.IMAP_SSL_DEFAULT_PORT or
            self.imap_config.get('use_ssl', True)
        )

    @property
    def folder(self) -> str:
        """
        Get the email folder to scan.
        """
        return self.filter_config.get(
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

        filters = self.filter_config.get('filters', [])
        criteria = [
            c
            for f in filters
            for c in self._process_filter_item(f)
        ]

        # Priority: use 'since' from config, then 'max_age_days'
        since_date = self.filter_config.get('since')
        if since_date:
            criteria.append(
                f'{self.SEARCH_CRITERIA_SINCE} "{since_date}"'
            )
        else:
            max_age_days = self.filter_config.get('max_age_days')
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
        from datetime import datetime, timedelta
        since_date = (
            datetime.now() - timedelta(days=max_age_days)
        ).strftime(self.IMAP_DATE_FORMAT)
        return since_date

    def _delete_email(self, message_number):
        """
        Delete email from IMAP server after fetching

        Args:
            message_number: IMAP message number to delete
        """
        try:
            self.imap_client.store(
                message_number,
                '+FLAGS',
                '\\Deleted'
            )

            self.imap_client.expunge()

            logger.info(
                f"[{self.user_context}] Deleted email {message_number} "
                f"from server"
            )
        except Exception as e:
            logger.error(
                f"[{self.user_context}] Failed to delete email "
                f"{message_number}: {e}"
            )

    def scan_emails(self) -> Generator[bytes, None, None]:
        """
        Scan emails from IMAP server and yield raw email data.
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

            delete_after_fetch = self.imap_config.get(
                'delete_after_fetch', False
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

                    yield raw_email

                    if delete_after_fetch:
                        self._delete_email(message_number)

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
