"""
OAuth-related views.

Handles OAuth authentication flow including Google setup
and OAuth callback redirects.
"""

import logging

from django.conf import settings
from django.db import transaction
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from django.views import View

from drf_spectacular.utils import extend_schema

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from threadline.models import EmailAlias, Settings
from threadline.utils.prompt_config_manager import PromptConfigManager

from ..models import Profile
from ..serializers import (
    CompleteGoogleSetupSerializer,
    SuccessResponseSerializer,
    UserDetailsSerializer,
)

logger = logging.getLogger(__name__)


class CompleteGoogleSetupView(APIView):
    """
    Complete OAuth user setup (Google, WeChat, GitHub, etc.)

    After OAuth authentication, user needs to complete setup
    by providing virtual email and preferences.
    No password required since they authenticate via OAuth provider.

    Note: Despite the class name, this view handles all OAuth providers.
    The name is kept for backward compatibility.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['auth'],
        summary=_("Complete OAuth user setup"),
        request=CompleteGoogleSetupSerializer,
        responses={200: SuccessResponseSerializer}
    )
    def post(self, request):
        """
        Complete OAuth user setup.

        Handles setup completion for all OAuth providers.
        """
        user = request.user

        try:
            profile = user.profile
        except Profile.DoesNotExist:
            profile = Profile.objects.create(user=user)

        if profile.registration_completed:
            return Response(
                {
                    'success': False,
                    'error': _(
                        'User has already completed registration'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = CompleteGoogleSetupSerializer(
            data=request.data
        )

        if not serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'errors': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        username = serializer.validated_data['virtual_email_username']
        scene = serializer.validated_data['scene']
        language = serializer.validated_data['language']
        timezone_str = serializer.validated_data['timezone']

        try:
            with transaction.atomic():
                user.username = username

                # Set password as unusable for OAuth users
                # They authenticate through Google, not password
                # If user wants password login later, they can set one
                user.set_unusable_password()
                user.save()

                profile.registration_completed = True
                profile.language = language
                profile.timezone = timezone_str
                profile.save()

                email_alias = EmailAlias.objects.create(
                    user=user,
                    alias=username,
                    is_active=True
                )
                logger.info(
                    f"Created email alias: "
                    f"{email_alias.full_email_address()}"
                )

                config_manager = PromptConfigManager()
                prompt_config = config_manager.generate_user_config(
                    language,
                    scene
                )

                Settings.objects.create(
                    user=user,
                    key='prompt_config',
                    value=prompt_config,
                    description='AI prompt configuration',
                    is_active=True
                )

                default_email_config = {
                    'mode': 'auto_assign',
                    'imap_config': {
                        'imap_host': '',
                        'smtp_ssl_port': 465,
                        'smtp_starttls_port': 587,
                        'imap_ssl_port': 993,
                        'username': '',
                        'password': '',
                        'use_ssl': True,
                        'use_starttls': False,
                        'delete_after_fetch': False
                    },
                    'filter_config': {
                        'filters': [],
                        'exclude_patterns': [],
                        'max_age_days': 30
                    }
                }

                Settings.objects.create(
                    user=user,
                    key='email_config',
                    value=default_email_config,
                    description='Email fetch configuration',
                    is_active=True
                )

                # Initialize Free Plan subscription and credits
                if settings.BILLING_ENABLED:
                    from accounts.services.registration import (
                        RegistrationService
                    )
                    RegistrationService._initialize_free_plan(user)

                logger.info(
                    f"Google user {user.username} completed setup"
                )

            refresh = RefreshToken.for_user(user)

            # Use UserDetailsSerializer to get complete user info including virtual_email
            user_serializer = UserDetailsSerializer(user)

            return Response(
                {
                    'success': True,
                    'message': _('Setup completed successfully'),
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                    'user': user_serializer.data
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(
                f"Failed to complete Google setup: {e}",
                exc_info=True
            )
            return Response(
                {
                    'success': False,
                    'error': _('Failed to complete setup')
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class OAuthCallbackRedirectView(View):
    """
    Generic OAuth callback redirect view.

    Generates JWT tokens for authenticated user and redirects to frontend
    with tokens in URL parameters.

    This view works for any OAuth provider (Google, WeChat, GitHub, etc.)
    by using a generic callback route.

    Note: Do NOT use @login_required decorator as it causes redirect loops.
    """

    def get(self, request, *args, **kwargs):
        """
        Handle OAuth callback redirect.

        Generate JWT tokens and redirect to frontend with tokens in URL.
        """
        user = request.user

        if user and user.is_authenticated:
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            redirect_url = (
                f"{settings.FRONTEND_URL}/auth/oauth/callback"
                f"?access_token={access_token}"
                f"&refresh_token={refresh_token}"
            )

            logger.info(
                f"OAuth redirect: {user.email} → "
                f"frontend with JWT tokens"
            )

            return redirect(redirect_url)

        logger.warning(
            "OAuth callback: user not authenticated, "
            "redirecting without tokens"
        )
        return redirect(f"{settings.FRONTEND_URL}/auth/oauth/callback")
