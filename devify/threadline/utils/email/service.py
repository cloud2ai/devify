"""
Email Save Service

Provides unified email saving functionality for both IMAP and Haraka email
processing.
"""

import logging
from typing import Dict, List, Optional

from django.contrib.auth.models import User
from django.utils import timezone

from threadline.models import EmailMessage, EmailStatus, EmailAlias

logger = logging.getLogger(__name__)


class EmailSaveService:
    """
    Email save service

    Responsibilities:
    1. Email saving logic
    2. Attachment processing logic
    3. User assignment logic
    4. Error handling
    """

    def __init__(self):
        # Cache user email mappings to avoid repeated queries
        self._user_email_cache = {}
        self._alias_cache = {}
        self._cache_loaded = False

    def save_email(
        self,
        user_id: int,
        email_data: Dict,
        task_id: Optional[int] = None
    ) -> EmailMessage:
        """
        Save email to database

        Args:
            user_id: User ID
            email_data: Parsed email data
            task_id: Optional task ID to associate with email

        Returns:
            EmailMessage instance
        """
        try:
            # Prepare create data
            create_data = {
                'user_id': user_id,
                'subject': email_data['subject'],
                'sender': email_data['sender'],
                'recipients': email_data['recipients'],
                'received_at': email_data['received_at'],
                'raw_content': email_data['raw_content'],
                'html_content': email_data.get('html_content', ''),
                'text_content': email_data.get('text_content', ''),
                'message_id': email_data['message_id'],
                'status': EmailStatus.FETCHED.value,
            }

            # Add task if provided
            if task_id:
                create_data['task_id'] = task_id

            # Create EmailMessage record
            email_msg = EmailMessage.objects.create(**create_data)

            # Process attachments
            attachments = email_data.get('attachments', [])
            if attachments:
                self.process_attachments(user_id, email_msg, attachments)

            return email_msg

        except Exception as exc:
            logger.error(f"Failed to save email to database: {exc}")
            raise

    def process_attachments(
        self,
        user_id: int,
        email_msg: EmailMessage,
        attachments: List[Dict]
    ):
        """
        Process email attachments

        Args:
            user_id: User ID
            email_msg: EmailMessage instance
            attachments: List of attachment data
        """
        try:
            # TODO: Implement attachment processing logic
            # This would involve:
            # 1. Saving attachment files to storage
            # 2. Creating EmailAttachment records
            # 3. Linking attachments to email message

            logger.info(
                f"Processing {len(attachments)} attachments for "
                f"email {email_msg.id}"
            )

        except Exception as exc:
            logger.error(
                f"Failed to process attachments: {exc}"
            )
            raise

    def find_user_by_recipient(self, email_data: Dict) -> Optional[User]:
        """
        Find user based on email recipient addresses (optimized version)

        Args:
            email_data: Parsed email data

        Returns:
            User instance or None if no user found
        """
        try:
            # Ensure cache is loaded
            self._load_user_cache()

            # Find user based on recipient addresses
            recipients = email_data.get('recipients', [])
            if not recipients:
                logger.warning("No recipients found in email")
                return None

            # Find matching users in cache
            for recipient in recipients:
                # 1. First check user email cache
                user_id = self._user_email_cache.get(recipient)
                if user_id:
                    user = User.objects.get(id=user_id)
                    logger.debug(f"Found user by email: {user.username}")
                    return user

                # 2. Check email aliases cache
                user_id = self._alias_cache.get(recipient)
                if user_id:
                    user = User.objects.get(id=user_id)
                    logger.debug(f"Found user by alias: {user.username}")
                    return user

            logger.warning(f"No user found for recipients: {recipients}")
            return None

        except Exception as exc:
            logger.error(f"Failed to find user by recipient: {exc}")
            return None

    def _load_user_cache(self):
        """
        Load user email and alias cache
        """
        if self._cache_loaded:
            return

        logger.info("Loading user email cache...")

        # Batch load all user emails
        users = User.objects.filter(is_active=True).values(
            'id', 'email'
        )
        for user in users:
            email = user['email']
            if email:
                self._user_email_cache[email] = user['id']

        # Batch load all email aliases
        aliases = EmailAlias.objects.filter(
            is_active=True
        ).values('alias', 'domain', 'user_id')
        for alias in aliases:
            email_address = f"{alias['alias']}@{alias['domain']}"
            self._alias_cache[email_address] = alias['user_id']

        self._cache_loaded = True
        logger.info(
            f"User cache loaded: {len(self._user_email_cache)} emails, "
            f"{len(self._alias_cache)} aliases"
        )

    def refresh_cache(self):
        """Refresh user cache"""
        self._cache_loaded = False
        self._user_email_cache.clear()
        self._alias_cache.clear()
        self._load_user_cache()
