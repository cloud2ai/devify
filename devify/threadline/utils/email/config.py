"""
Email Configuration Manager

Provides utilities for managing email configurations and detecting email sources.
"""

import logging
from enum import Enum
from typing import Dict, Optional

from django.contrib.auth.models import User
from django.utils import timezone

from threadline.models import Settings

logger = logging.getLogger(__name__)


class EmailSource(Enum):
    """Email source types"""
    IMAP = "IMAP_EMAIL_FETCH"
    FILE = "HARAKA_EMAIL_FETCH"


class EmailConfigManager:
    """
    Email configuration manager utility class

    Location: devify/threadline/utils/email/config.py

    Responsibilities:
    1. Configuration detection
    2. Configuration validation
    3. Configuration updates
    """

    @staticmethod
    def detect_email_source(user_id: int) -> EmailSource:
        """
        Detect user email source type

        Args:
            user_id: User ID

        Returns:
            EmailSource enum value
        """
        try:
            email_config = EmailConfigManager.get_email_config(user_id)

            # Check if has imap_config
            if 'imap_config' in email_config:
                return EmailSource.IMAP
            # Check if has file_config or auto_assign mode
            elif (
                'file_config' in email_config or
                email_config.get('mode') == 'auto_assign'
            ):
                return EmailSource.FILE
            else:
                # Default to IMAP mode (backward compatibility)
                return EmailSource.IMAP

        except Exception as exc:
            logger.error(
                f"Failed to detect email source for user {user_id}: {exc}"
            )
            return EmailSource.IMAP

    @staticmethod
    def get_email_config(user_id: int) -> Dict:
        """
        Get user email configuration

        Args:
            user_id: User ID

        Returns:
            Email configuration dictionary
        """
        try:
            email_setting = Settings.objects.get(
                user_id=user_id,
                key='email_config',
                is_active=True
            )
            return email_setting.value

        except Settings.DoesNotExist:
            logger.warning(f"No email_config found for user {user_id}")
            return {}

    @staticmethod
    def update_fetch_time(
        user_id: int, last_fetch_time: timezone.datetime
    ):
        """
        Update last fetch time

        Args:
            user_id: User ID
            last_fetch_time: Last fetch time
        """
        try:
            email_config = EmailConfigManager.get_email_config(user_id)
            if email_config:
                email_config['filter_config'][
                    'last_email_fetch_time'
                ] = last_fetch_time.isoformat()

                Settings.objects.filter(
                    user_id=user_id,
                    key='email_config',
                    is_active=True
                ).update(value=email_config)

        except Exception as exc:
            logger.error(
                f"Failed to update fetch time: {exc}"
            )

    @staticmethod
    def validate_imap_config(config: Dict) -> bool:
        """
        Validate IMAP configuration

        Args:
            config: IMAP configuration dictionary

        Returns:
            True if configuration is valid
        """
        required_fields = ['host', 'port', 'username', 'password']
        imap_config = config.get('imap_config', {})

        for field in required_fields:
            if not imap_config.get(field):
                logger.warning(f"Missing required IMAP field: {field}")
                return False

        # Validate port number
        port = imap_config.get('port')
        if not isinstance(port, int) or port <= 0 or port > 65535:
            logger.warning(f"Invalid IMAP port: {port}")
            return False

        return True

    @staticmethod
    def update_fetch_config(user_id: int, config: Dict) -> bool:
        """
        Update fetch configuration

        Args:
            user_id: User ID
            config: New configuration

        Returns:
            True if update successful
        """
        try:
            # Validate configuration
            if not EmailConfigManager.validate_imap_config(config):
                return False

            # Update configuration
            Settings.objects.filter(
                user_id=user_id,
                key='email_config',
                is_active=True
            ).update(value=config)

            logger.info(f"Email config updated for user {user_id}")
            return True

        except Exception as exc:
            logger.error(f"Failed to update fetch config: {exc}")
            return False
