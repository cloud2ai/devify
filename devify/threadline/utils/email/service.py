"""
Email Save Service

Provides unified email saving functionality for both IMAP and Haraka email
processing.
"""

import logging
import os
import shutil
from django.conf import settings
from typing import Dict, List, Optional

from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone
from django.conf import settings

from threadline.models import (
    EmailAlias,
    EmailAttachment,
    EmailMessage,
    EmailStatus,
    Settings,
)

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
        self._email_to_user_map = {}
        self._user_cache = {}
        self._mappings_loaded = False

    def save_email(
        self,
        user_id: int,
        email_data: Dict
    ) -> EmailMessage:
        """
        Save email to database

        Args:
            user_id: User ID
            email_data: Parsed email data

        Returns:
            EmailMessage instance or None if duplicate

        Note:
            Uses get_or_create to handle duplicate emails gracefully.
            If email already exists (same user_id + message_id),
            returns None to skip processing.
        """
        try:
            create_data = {
                'subject': email_data['subject'],
                'sender': email_data['sender'],
                'recipients': email_data['recipients'],
                'received_at': email_data['received_at'],
                'raw_content': email_data['raw_content'],
                'html_content': email_data.get('html_content', ''),
                'text_content': email_data.get('text_content', ''),
                'status': EmailStatus.FETCHED.value,
            }

            # Use get_or_create to handle duplicate emails
            email_msg, created = EmailMessage.objects.get_or_create(
                user_id=user_id,
                message_id=email_data['message_id'],
                defaults=create_data
            )

            if not created:
                logger.info(
                    f"Email already exists: {email_data['message_id']}, "
                    f"skipping"
                )
                return None

            logger.info(
                f"Saved new email: {email_msg.id} "
                f"(message_id: {email_data['message_id']})"
            )

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
        Process email attachments from parsed metadata

        Args:
            user_id: User ID
            email_msg: EmailMessage instance
            attachments: List of attachment metadata from parser
        """
        try:
            logger.info(
                f"Processing {len(attachments)} attachments for "
                f"email {email_msg.id}"
            )

            # Create email-specific attachment directory using UUID
            user_attachment_dir = os.path.join(
                settings.EMAIL_ATTACHMENT_DIR,
                str(email_msg.uuid)
            )
            os.makedirs(user_attachment_dir, exist_ok=True)

            for attachment_data in attachments:
                try:
                    # Extract attachment information from parser metadata
                    filename = attachment_data.get('filename', 'unknown')
                    content_type = attachment_data.get(
                        'content_type',
                        'application/octet-stream'
                    )
                    file_size = attachment_data.get('file_size', 0)
                    source_file_path = attachment_data.get('file_path', '')
                    # Get safe filename for attachment.
                    # Fallback to original filename if safe_filename is not
                    # present.
                    safe_filename = attachment_data.get(
                        'safe_filename', filename
                    )

                    # Skip processing if source file path is missing or file
                    # does not exist
                    if (
                        not source_file_path or
                        not os.path.exists(source_file_path)
                    ):
                        logger.warning(
                            f"Skipping attachment {filename}: "
                            f"file not found at {source_file_path}"
                        )
                        continue

                    # Copy file to user-specific directory
                    dest_file_path = os.path.join(
                        user_attachment_dir, safe_filename)
                    shutil.copy2(source_file_path, dest_file_path)

                    # Determine if it's an image
                    is_image = content_type.startswith('image/')

                    # Create EmailAttachment record
                    EmailAttachment.objects.create(
                        user_id=user_id,
                        email_message=email_msg,
                        filename=filename,
                        safe_filename=safe_filename,
                        content_type=content_type,
                        file_size=file_size,
                        file_path=dest_file_path,
                        is_image=is_image
                    )

                    logger.info(
                        f"Attachment {filename} processed successfully, "
                        f"size={file_size} bytes, copied to {dest_file_path}"
                    )

                except Exception as exc:
                    logger.error(f"Failed to process attachment "
                                 f"{filename}: {exc}")
                    continue

            logger.info(f"Successfully processed {len(attachments)} "
                        f"attachments")

        except Exception as exc:
            logger.error(
                f"Failed to process attachments: {exc}"
            )
            raise

    def load_user_mappings(self):
        """
        Load auto_assign users and their aliases into memory for batch
        processing optimization.
        Only loads users who have auto_assign mode enabled.
        This method should be called once at the start of batch
        email processing.
        """
        if self._mappings_loaded:
            return

        logger.info("Loading auto_assign user mappings for batch processing...")

        # Get all email configs and filter in Python due to JSONField query limitations
        all_email_settings = Settings.objects.filter(
            key='email_config',
            is_active=True
        ).values('user_id', 'value')

        auto_assign_user_ids = {
            setting['user_id']
            for setting in all_email_settings
            if setting['value'].get('mode') == 'auto_assign'
        }

        if not auto_assign_user_ids:
            logger.info("No auto_assign users found")
            self._mappings_loaded = True
            return

        users = User.objects.filter(
            id__in=auto_assign_user_ids,
            is_active=True
        ).values('id', 'email', 'username')

        default_domain = settings.AUTO_ASSIGN_EMAIL_DOMAIN
        aliases = EmailAlias.objects.filter(
            user_id__in=auto_assign_user_ids,
            is_active=True
        ).values('alias', 'user_id')

        alias_map = {alias['user_id']: alias['alias'] for alias in aliases}

        for user in users:
            user_id = user['id']

            if user_id in alias_map:
                alias = alias_map[user_id]
                email_address = f"{alias}@{default_domain}"
            else:
                email_address = f"{user['username']}@{default_domain}"

            self._user_cache[user_id] = {
                'id': user_id,
                'email': email_address,
                'username': user['username']
            }

            self._email_to_user_map[email_address] = user_id

        self._mappings_loaded = True

    def find_user_by_recipient(self, email_data: Dict) -> Optional[User]:
        """
        Find user based on email recipient addresses (optimized batch version)

        Args:
            email_data: Parsed email data

        Returns:
            User instance or None if no user found
        """
        try:
            recipients = email_data.get('recipients', [])
            if not recipients:
                logger.warning("No recipients found in email")
                return None

            for recipient in recipients:
                user_id = self._email_to_user_map.get(recipient)
                if user_id:
                    user_data = self._user_cache[user_id]
                    logger.debug(
                        f"Found user: {user_data['username']}"
                    )
                    user = User(
                        id=user_data['id'],
                        email=user_data['email'],
                        username=user_data['username']
                    )
                    return user

            logger.warning(f"No user found for recipients: {recipients}")
            return None

        except Exception as exc:
            logger.error(f"Failed to find user by recipient: {exc}")
            return None
