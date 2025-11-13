"""
Registration service for handling user registration operations.
"""

import logging
import re
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from accounts.models import Profile
from threadline.models import EmailAlias, Settings
from threadline.utils.prompt_config_manager import PromptConfigManager

logger = logging.getLogger(__name__)


class RegistrationService:
    """
    Service class for handling user registration operations.
    Provides atomic operations for creating users with complete
    configuration.
    """

    @staticmethod
    def generate_registration_token() -> str:
        """
        Generate a secure random token for registration verification.

        Returns:
            str: A secure random token (64 characters)
        """
        return secrets.token_urlsafe(48)

    @staticmethod
    def calculate_token_expiry():
        """
        Calculate token expiration datetime.

        Returns:
            datetime: Token expiration datetime
        """
        return (
            timezone.now() +
            timedelta(hours=settings.REGISTRATION_TOKEN_EXPIRY_HOURS)
        )

    @staticmethod
    def is_token_valid(token: str, expires_at) -> bool:
        """
        Check if registration token is still valid.

        Args:
            token: Registration token
            expires_at: Token expiration datetime

        Returns:
            bool: True if token is valid, False otherwise
        """
        if not token or not expires_at:
            return False

        return timezone.now() < expires_at

    @staticmethod
    def validate_virtual_email_alias(alias: str) -> tuple[bool, str]:
        """
        Validate virtual email alias format and uniqueness.

        Format requirements:
        - Length: 3-64 characters
        - Characters: letters, numbers, dots, underscore, hyphen
        - Must start with letter or number
        - Must end with letter or number
        - Cannot start or end with dot

        Args:
            alias: Virtual email alias to validate

        Returns:
            tuple: (is_valid, error_message)
                - (True, '') if valid
                - (False, error_message) if invalid
        """
        if not alias:
            return False, 'Alias cannot be empty'

        if len(alias) < 3 or len(alias) > 64:
            return (
                False,
                'Alias must be between 3 and 64 characters'
            )

        if alias.startswith('.') or alias.endswith('.'):
            return (
                False,
                'Username cannot start or end with a dot'
            )

        pattern = r'^[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9]$'
        if len(alias) == 3:
            pattern = r'^[a-zA-Z0-9.]{3}$'

        if not re.match(pattern, alias):
            return (
                False,
                'Alias must start and end with letter or number, '
                'and can only contain letters, numbers, dots, '
                'underscores, and hyphens'
            )

        if not EmailAlias.is_unique(alias):
            return False, 'This virtual email is already taken'

        return True, ''

    @staticmethod
    def _initialize_free_plan(user):
        """
        Initialize Free Plan subscription and credits for new user.

        Creates a Free Plan subscription with initial credits.
        This runs automatically during registration when billing
        is enabled.

        Args:
            user: Django User instance

        Raises:
            Exception: If billing initialization fails

        Note:
            Imports billing models locally to avoid import errors
            when BILLING_ENABLED=False or billing app not installed.
        """
        # Local import to avoid circular dependency and conditional loading
        from billing.models import (
            Plan,
            UserCredits,
            Subscription,
            PaymentProvider
        )

        try:
            free_plan = Plan.objects.get(slug='free')
            payment_provider = PaymentProvider.objects.get(name='stripe')

            current_time = timezone.now()
            period_days = free_plan.metadata.get('period_days', 30)
            period_end = current_time + timedelta(days=period_days)
            base_credits = free_plan.metadata.get(
                'credits_per_period', 10
            )

            # Create Free Plan subscription
            subscription = Subscription.objects.create(
                user=user,
                plan=free_plan,
                provider=payment_provider,
                status='active',
                current_period_start=current_time,
                current_period_end=period_end,
                auto_renew=False
            )

            # Initialize user credits
            UserCredits.objects.create(
                user=user,
                subscription=subscription,
                base_credits=base_credits,
                bonus_credits=0,
                consumed_credits=0,
                period_start=current_time,
                period_end=period_end,
                is_active=True
            )

            logger.info(
                f"Initialized Free Plan for user {user.username}: "
                f"{base_credits} credits, {period_days} days period"
            )

        except Exception as e:
            logger.warning(
                f"Failed to initialize Free Plan for user "
                f"{user.username}: {e}"
            )
            raise

    @staticmethod
    @transaction.atomic
    def create_user_with_config(
        email: str,
        password: str,
        username: str,
        scene: str,
        language: str,
        timezone_str: str
    ) -> User:
        """
        Create user with complete configuration in atomic transaction.

        This method performs the following operations atomically:
        1. Create User and Profile
        2. Create EmailAlias for virtual email
        3. Initialize prompt_config based on scene and language
        4. Initialize email_config for auto_assign mode

        Args:
            email: User's real email address (for login)
            password: User's password
            username: Custom username for virtual email
            scene: User's selected scene (chat, product_issue, etc.)
            language: AI output language for summaries, titles,
                      and metadata (zh-CN, en-US, es)
            timezone_str: User's timezone

        Returns:
            User: Created user instance

        Raises:
            ValueError: If validation fails or configuration error
            Exception: If any step in the creation process fails
        """
        is_valid, error_msg = (
            RegistrationService.validate_virtual_email_alias(
                username
            )
        )
        if not is_valid:
            raise ValueError(f'Invalid virtual email username: {error_msg}')

        if User.objects.filter(email=email).exists():
            raise ValueError('Email already exists')

        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            logger.info(f"Created user: {username}")

            Profile.objects.create(
                user=user,
                registration_completed=True,
                language=language,
                timezone=timezone_str
            )
            logger.info(f"Created profile for user: {username}")

            EmailAlias.objects.create(
                user=user,
                alias=username,
                is_active=True
            )
            logger.info(
                f"Created email alias: "
                f"{username}@"
                f"{settings.AUTO_ASSIGN_EMAIL_DOMAIN}"
            )

            prompt_manager = PromptConfigManager()
            prompt_config = prompt_manager.generate_user_config(
                language=language,
                scene=scene
            )

            Settings.objects.create(
                user=user,
                key='prompt_config',
                value=prompt_config,
                description='User prompt configuration',
                is_active=True
            )
            logger.info(
                f"Created prompt_config for user: {username} "
                f"(scene: {scene}, language: {language})"
            )

            email_config = {
                'mode': 'auto_assign'
            }

            Settings.objects.create(
                user=user,
                key='email_config',
                value=email_config,
                description='User email configuration',
                is_active=True
            )
            logger.info(
                f"Created email_config for user: {username} "
                f"(mode: auto_assign)"
            )

            # Initialize Free Plan subscription and credits
            if settings.BILLING_ENABLED:
                RegistrationService._initialize_free_plan(user)

            return user

        except Exception as e:
            logger.error(
                f"Failed to create user with config: {e}",
                exc_info=True
            )
            raise

    @staticmethod
    def create_registration_token(
        email: str,
        language: str
    ) -> tuple[str, Profile]:
        """
        Create or update a registration token for email registration.

        Creates a temporary user and profile with registration token
        if user doesn't exist. Updates token if user exists but
        registration is not completed.

        Args:
            email: User's email address
            language: User's preferred language

        Returns:
            tuple: (token, profile)

        Raises:
            ValueError: If user exists and registration is completed
        """
        token = RegistrationService.generate_registration_token()
        expires_at = (
            timezone.now() +
            timedelta(
                hours=settings.REGISTRATION_TOKEN_EXPIRY_HOURS
            )
        )

        try:
            user = User.objects.get(email=email)

            try:
                profile = Profile.objects.get(user=user)
            except Profile.DoesNotExist:
                profile = Profile.objects.create(
                    user=user,
                    registration_completed=False,
                    registration_token=token,
                    registration_token_expires=expires_at,
                    language=language
                )
                logger.info(
                    f"Created profile for existing user: {user.username}"
                )
                return token, profile

            if profile.registration_completed:
                raise ValueError(
                    'User already exists and registration is completed'
                )

            profile.registration_token = token
            profile.registration_token_expires = expires_at
            profile.language = language
            profile.save()

            logger.info(
                f"Updated registration token for existing user: "
                f"{user.username}"
            )

        except User.DoesNotExist:
            username = email.split('@')[0]
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            user = User.objects.create_user(
                username=username,
                email=email,
                password=None
            )
            user.set_unusable_password()
            user.save()

            profile = Profile.objects.create(
                user=user,
                registration_completed=False,
                registration_token=token,
                registration_token_expires=expires_at,
                language=language
            )

            logger.info(
                f"Created temporary user and profile for: {email}"
            )

        return token, profile

    @staticmethod
    def verify_registration_token(token: str) -> tuple[bool, Profile]:
        """
        Verify registration token validity and expiration.

        Args:
            token: Registration token to verify

        Returns:
            tuple: (is_valid, profile)
                - (True, profile) if valid
                - (False, None) if invalid or expired
        """
        try:
            profile = Profile.objects.get(
                registration_token=token,
                registration_completed=False
            )

            if (
                profile.registration_token_expires and
                profile.registration_token_expires < timezone.now()
            ):
                logger.warning(
                    f"Registration token expired for user: "
                    f"{profile.user.username}"
                )
                return False, None

            return True, profile

        except Profile.DoesNotExist:
            logger.warning(
                f"Registration token not found or already used: {token}"
            )
            return False, None
