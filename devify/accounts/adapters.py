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

    def populate_user(self, request, sociallogin, data):
        """
        Populate user with OAuth data.
        Generate a unique username if not provided.
        """
        user = super().populate_user(request, sociallogin, data)

        if not user.username or user.username == '':
            email = data.get('email', '')
            if email:
                base_username = email.split('@')[0]
            else:
                base_username = f"user_{uuid.uuid4().hex[:8]}"

            username = base_username
            counter = 1
            from django.contrib.auth import get_user_model
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
        """
        user = sociallogin.user

        if user.pk:
            try:
                profile = user.profile
            except Profile.DoesNotExist:
                Profile.objects.create(
                    user=user,
                    registration_completed=False
                )
                logger.info(f"Created profile for existing user: {user.email}")

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
