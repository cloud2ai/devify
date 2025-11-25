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

from allauth.socialaccount.adapter import (
    DefaultSocialAccountAdapter
)
from django.contrib.auth import get_user_model
from django.conf import settings

from .models import Profile


logger = logging.getLogger(__name__)


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom social account adapter for OAuth users.
    Handles business logic for user creation, profile setup, and redirects.
    """

    def is_auto_signup_allowed(self, request, sociallogin):
        """
        Allow automatic signup for OAuth users.
        This prevents allauth from showing the signup form.
        """
        return True

    def get_login_redirect_url(self, request):
        """
        Redirect to custom OAuth callback view after login.

        The custom view will generate JWT tokens and redirect to frontend.
        """
        return settings.LOGIN_REDIRECT_URL

    def get_signup_redirect_url(self, request):
        """
        Redirect to custom OAuth callback view after signup.

        This prevents allauth from showing Django template signup form.
        The custom view will generate JWT tokens and redirect to frontend.
        """
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
        # Provider-specific field mappings
        provider_field_map = {
            'google': {
                'first_name': 'given_name',
                'last_name': 'family_name',
            },
            # Add more providers as needed
            # 'github': {
            #     'first_name': 'name',
            #     'last_name': None
            # },
            # 'facebook': {
            #     'first_name': 'first_name',
            #     'last_name': 'last_name'
            # },
        }

        # Try provider-specific mapping first
        if provider in provider_field_map:
            field_map = provider_field_map[provider]
            first_name = data.get(field_map['first_name'], '').strip()
            first_name = first_name or None

            last_name = ''
            if field_map.get('last_name'):
                last_name = data.get(field_map['last_name'], '').strip()
            last_name = last_name or None

            return (first_name, last_name)

        # Fallback: try to extract from 'name' field if user has no names
        if not user.first_name and not user.last_name:
            full_name = data.get('name', '').strip()
            if full_name:
                name_parts = full_name.split(None, 1)
                if len(name_parts) >= 2:
                    return (name_parts[0], name_parts[1])
                elif len(name_parts) == 1:
                    return (name_parts[0], None)

        # If user already has names from django-allauth, use them
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

        # Save immediately for existing users
        if updated and user.pk and updated_fields:
            user.save(update_fields=updated_fields)

        return updated

    def populate_user(self, request, sociallogin, data):
        """
        Populate user with OAuth data.
        Generate a unique username if not provided.

        Syncs first_name and last_name for both new and existing users
        to keep data up-to-date from OAuth provider.

        OAuth providers typically provide:
        - Google: given_name (first_name), family_name (last_name)
        - Other providers: name (may need to be split)
        - email
        These are automatically mapped by django-allauth via
        super().populate_user(), but we ensure they are properly set.
        """
        user = super().populate_user(request, sociallogin, data)

        # Extract names from OAuth provider data
        provider = sociallogin.account.provider
        first_name, last_name = self._extract_names_from_oauth_data(
            provider, data, user
        )

        # Log OAuth data for debugging (Google provider)
        if provider == 'google':
            logger.info(
                f"Google OAuth user data: "
                f"given_name={data.get('given_name', 'N/A')}, "
                f"family_name={data.get('family_name', 'N/A')}, "
                f"email={data.get('email', 'N/A')}"
            )

        # Update user names if available
        # For new users, names will be saved in save_user()
        # For existing users, names are saved immediately
        self._update_user_names(user, first_name, last_name)

        # Generate unique username if user doesn't have one
        # OAuth providers may not provide username, so we generate one
        # based on email address or a random UUID
        if not user.username or user.username == '':
            email = data.get('email', '')
            if email:
                # Use email prefix as base username
                base_username = email.split('@')[0]
            else:
                # Fallback to random username if no email available
                base_username = f"user_{uuid.uuid4().hex[:8]}"

            # Ensure username uniqueness by appending counter if needed
            # This handles cases where multiple users have same email prefix
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
        user = sociallogin.user

        # Only process existing users (user.pk exists)
        if user.pk:
            # Check if profile exists, create if not
            # Use get_or_create to avoid race conditions
            Profile.objects.get_or_create(
                    user=user,
                defaults={
                    'registration_completed': False
                }
                )

    def save_user(self, request, sociallogin, form=None):
        """
        Create new OAuth user.
        Set password as unusable and mark registration incomplete.
        """
        user = super().save_user(request, sociallogin, form)

        user.set_unusable_password()
        user.save()

        Profile.objects.create(
            user=user,
            registration_completed=False
        )

        logger.info(
            f"OAuth user created: {user.email} "
            f"(provider: {sociallogin.account.provider})"
        )

        return user
