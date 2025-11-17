"""
Django signals for automatic user setup

This module provides signals to automatically create EmailAlias and
Profile when a user is created, regardless of how the user was created
(Django admin, API, management commands, etc.)
"""

import logging

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import Profile

try:
    from threadline.models import EmailAlias
except ImportError:
    EmailAlias = None

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_user_resources(sender, instance, created, **kwargs):
    """
    Automatically create EmailAlias and Profile when a user is created

    This signal ensures that all users have the necessary resources
    regardless of how they were created (Django admin, API, etc.)
    """
    if not created:
        return

    try:
        with transaction.atomic():
            create_email_alias(instance)
            create_profile(instance)
    except Exception as e:
        logger.warning(
            f"Failed to create resources for user "
            f"{instance.username}: {e}",
            exc_info=True
        )


def create_email_alias(user):
    """
    Create EmailAlias for user if it doesn't exist
    """
    if EmailAlias is None:
        logger.warning(
            "EmailAlias model not found, skipping email alias creation"
        )
        return None

    try:
        existing_alias = EmailAlias.objects.filter(
            user=user,
            is_active=True
        ).first()

        if existing_alias:
            return existing_alias

        if EmailAlias.objects.filter(alias=user.username).exists():
            logger.warning(
                f"Username {user.username} already used as alias by "
                f"another user. Skipping EmailAlias creation for user "
                f"{user.username}"
            )
            return None

        alias = EmailAlias.objects.create(
            user=user,
            alias=user.username,
            is_active=True
        )
        logger.info(
            f"Created email alias {alias.full_email_address()} "
            f"for user {user.username}"
        )
        return alias
    except Exception as e:
        logger.warning(
            f"Failed to create email alias for user {user.username}: {e}"
        )
        return None


def create_profile(user):
    """
    Create Profile for user if it doesn't exist
    """
    if Profile is None:
        logger.warning(
            "Profile model not found, skipping profile creation"
        )
        return None

    try:
        profile, created = Profile.objects.get_or_create(
            user=user,
            defaults={
                'registration_completed': False,
                'language': 'en-US',
                'timezone': 'UTC'
            }
        )
        if created:
            logger.info(f"Created profile for user {user.username}")
        return profile
    except Exception as e:
        logger.warning(
            f"Failed to create profile for user {user.username}: {e}"
        )
        return None
