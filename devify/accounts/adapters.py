"""
Custom adapters for django-allauth.

These adapters customize the default behavior of allauth
to fit our OAuth registration flow requirements.

Key Features:
1. Auto-signup for OAuth users (no confirmation form)
2. Email-based account linking (existing emails auto-connect to OAuth)
3. Custom redirect to JWT token generation view
4. Automatic Profile creation for new and existing users
5. Username generation for users without usernames

OAuth Flow:
User authenticates with Google → allauth creates/links account →
Custom adapter redirects to /accounts/oauth/callback/ →
OAuthCallbackRedirectView generates JWT tokens →
Redirects to frontend with tokens in URL parameters
"""

import logging
import uuid

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.contrib.auth import get_user_model

from .models import Profile


logger = logging.getLogger(__name__)


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom social account adapter for OAuth users.
    Handles business logic for user creation, profile setup, and redirects.
    """

    def is_auto_signup_allowed(self, request, sociallogin):
        """Allow automatic signup for OAuth users without showing a form."""
        return True

    def get_login_redirect_url(self, request):
        """Redirect to custom OAuth callback view after login."""
        return settings.LOGIN_REDIRECT_URL

    def get_signup_redirect_url(self, request):
        """Redirect to custom OAuth callback view after signup."""
        return settings.LOGIN_REDIRECT_URL

    def _extract_names_from_oauth_data(self, provider, data, user):
        """
        Extract first_name and last_name from OAuth provider data.

        Different providers use different field names:
        - Google: given_name, family_name
        - GitHub/Facebook/etc: name (needs to be split)
        - django-allauth may have already populated these fields

        Returns:
            tuple: (first_name, last_name) or (None, None) if not available
        """
        provider_field_map = {
            'google': {
                'first_name': 'given_name',
                'last_name': 'family_name',
            },
        }

        if provider in provider_field_map:
            field_map = provider_field_map[provider]
            first_name = data.get(field_map['first_name'], '').strip() or None
            last_name = ''
            if field_map.get('last_name'):
                last_name = data.get(field_map['last_name'], '').strip()
            return (first_name, last_name or None)

        if not user.first_name and not user.last_name:
            full_name = data.get('name', '').strip()
            if full_name:
                name_parts = full_name.split(None, 1)
                if len(name_parts) >= 2:
                    return (name_parts[0], name_parts[1])
                elif len(name_parts) == 1:
                    return (name_parts[0], None)

        return (user.first_name or None, user.last_name or None)

    def _update_user_names(self, user, first_name, last_name):
        """
        Update user's first_name and last_name if they differ.

        Returns:
            bool: True if any name was updated, False otherwise
        """
        updated_fields = []
        updated = False

        if first_name and user.first_name != first_name:
            user.first_name = first_name
            updated_fields.append('first_name')
            updated = True
            logger.info(
                f"Updated first_name for user "
                f"{user.email or 'new'}: {first_name}"
            )

        if last_name and user.last_name != last_name:
            user.last_name = last_name
            updated_fields.append('last_name')
            updated = True
            logger.info(
                f"Updated last_name for user "
                f"{user.email or 'new'}: {last_name}"
            )

        if updated and user.pk and updated_fields:
            user.save(update_fields=updated_fields)

        return updated

    def populate_user(self, request, sociallogin, data):
        """
        Populate user with OAuth data and generate a unique username.

        Syncs first_name and last_name for both new and existing users
        to keep data up-to-date from the OAuth provider.
        """
        user = super().populate_user(request, sociallogin, data)

        provider = sociallogin.account.provider
        first_name, last_name = self._extract_names_from_oauth_data(
            provider, data, user
        )

        if provider == 'google':
            logger.info(
                f"Google OAuth user data: "
                f"given_name={data.get('given_name', 'N/A')}, "
                f"family_name={data.get('family_name', 'N/A')}, "
                f"email={data.get('email', 'N/A')}"
            )

        self._update_user_names(user, first_name, last_name)

        if not user.username:
            email = data.get('email', '')
            base_username = (
                email.split('@')[0] if email
                else f"user_{uuid.uuid4().hex[:8]}"
            )
            username = base_username
            counter = 1
            User = get_user_model()
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1
            user.username = username
            logger.info(f"Generated username: {username}")

        return user

    def pre_social_login(self, request, sociallogin):
        """
        Called after OAuth authentication but before login processing.
        Create Profile for existing users if needed.

        This is necessary because signals only trigger on user creation
        (created=True), not when existing users log in via OAuth.
        """
        # FIXME(Ray): Profile creation is split across pre_social_login
        # and save_user. pre_social_login handles existing Django users
        # connecting a new OAuth provider, while save_user covers all new
        # social accounts (including that same case). Both use get_or_create
        # to avoid IntegrityError, but the duplication is fragile.
        # Consolidate Profile creation into save_user only and remove this
        # block.
        user = sociallogin.user
        if user and user.pk:
            Profile.objects.get_or_create(
                user=user,
                defaults={'registration_completed': False},
            )

    def save_user(self, request, sociallogin, form=None):
        """
        Save OAuth user, set unusable password, and ensure Profile exists.
        """
        user = super().save_user(request, sociallogin, form)

        user.set_unusable_password()
        user.save()

        Profile.objects.get_or_create(
            user=user,
            defaults={'registration_completed': False},
        )

        logger.info(
            f"OAuth user created: {getattr(user, 'email', user.pk)} "
            f"(provider: {sociallogin.account.provider})"
        )

        return user
