"""
Shared user bootstrap helpers.

This module centralizes the standard initialization that should happen
after a user account is created, regardless of whether the entry point is
registration, OAuth setup, or admin-managed creation.
"""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.db import transaction

from accounts.models import Profile
from threadline.models import EmailAlias, Settings
from threadline.utils.prompt_config_manager import PromptConfigManager

logger = logging.getLogger(__name__)


class UserBootstrapService:
    """Create the standard user-side resources for a newly created user."""

    @staticmethod
    def build_auto_assign_email_config() -> dict[str, Any]:
        """Build the minimal auto-assign email configuration."""
        return {
            "mode": "auto_assign",
        }

    @staticmethod
    def build_oauth_email_config() -> dict[str, Any]:
        """Build the richer email config used by OAuth setup."""
        return {
            "mode": "auto_assign",
            "imap_config": {
                "imap_host": "",
                "smtp_ssl_port": 465,
                "smtp_starttls_port": 587,
                "imap_ssl_port": 993,
                "username": "",
                "password": "",
                "use_ssl": True,
                "use_starttls": False,
                "delete_after_fetch": False,
            },
            "filter_config": {
                "filters": [],
                "exclude_patterns": [],
                "max_age_days": 30,
            },
        }

    @staticmethod
    def _build_prompt_config(
        language: str,
        scene: str | None,
    ) -> dict[str, Any]:
        prompt_manager = PromptConfigManager()
        return prompt_manager.generate_user_config(
            language=language,
            scene=scene or settings.DEFAULT_SCENE,
        )

    @staticmethod
    def _upsert_profile(user, language: str, timezone_str: str):
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.language = language
        profile.timezone = timezone_str
        profile.registration_completed = True
        profile.save(
            update_fields=[
                "language",
                "timezone",
                "registration_completed",
            ]
        )
        return profile

    @staticmethod
    def _upsert_email_alias(user, alias: str | None = None):
        alias_name = (alias or user.username).strip()

        existing_alias = EmailAlias.objects.filter(
            user=user,
            alias=alias_name,
            is_active=True,
        ).first()
        if existing_alias:
            return existing_alias

        conflicting_alias = EmailAlias.objects.filter(alias=alias_name).first()
        if conflicting_alias and conflicting_alias.user != user:
            raise ValueError(
                "Email alias "
                f"'{alias_name}' already exists for another user"
            )

        if conflicting_alias:
            conflicting_alias.user = user
            conflicting_alias.is_active = True
            conflicting_alias.save(update_fields=["user", "is_active"])
            return conflicting_alias

        return EmailAlias.objects.create(
            user=user,
            alias=alias_name,
            is_active=True,
        )

    @staticmethod
    def _upsert_setting(
        user,
        *,
        key: str,
        value: dict[str, Any],
        description: str,
    ):
        setting, _ = Settings.objects.update_or_create(
            user=user,
            key=key,
            defaults={
                "value": value,
                "description": description,
                "is_active": True,
            },
        )
        return setting

    @staticmethod
    def _initialize_free_plan(user):
        """Delegate free-plan setup to the registration service."""
        from accounts.services.registration import RegistrationService

        RegistrationService._initialize_free_plan(user)

    @staticmethod
    @transaction.atomic
    def bootstrap_user(
        user,
        *,
        language: str,
        timezone_str: str,
        scene: str | None,
        email_config: dict[str, Any],
        prompt_description: str,
        email_description: str,
        email_alias: str | None = None,
        initialize_billing: bool = True,
    ):
        """
        Create or refresh the standard user resources.

        This method is intentionally idempotent so callers can use it after
        user creation even when a signal has already created part of the
        state.
        """
        profile = UserBootstrapService._upsert_profile(
            user,
            language=language,
            timezone_str=timezone_str,
        )
        email_alias_obj = UserBootstrapService._upsert_email_alias(
            user,
            alias=email_alias,
        )

        prompt_config = UserBootstrapService._build_prompt_config(
            language=language,
            scene=scene,
        )
        prompt_setting = UserBootstrapService._upsert_setting(
            user,
            key="prompt_config",
            value=prompt_config,
            description=prompt_description,
        )
        email_setting = UserBootstrapService._upsert_setting(
            user,
            key="email_config",
            value=email_config,
            description=email_description,
        )

        if initialize_billing and getattr(settings, "BILLING_ENABLED", False):
            UserBootstrapService._initialize_free_plan(user)

        logger.info(
            (
                "Bootstrapped user %s "
                "(profile=%s, alias=%s, prompt=%s, email=%s, billing=%s)"
            ),
            user.username,
            bool(profile),
            bool(email_alias_obj),
            bool(prompt_setting),
            bool(email_setting),
            bool(
                initialize_billing
                and getattr(settings, "BILLING_ENABLED", False)
            ),
        )
        return {
            "profile": profile,
            "email_alias": email_alias_obj,
            "prompt_config": prompt_setting,
            "email_config": email_setting,
        }
