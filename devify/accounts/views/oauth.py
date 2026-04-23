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

from ..models import Profile
from ..serializers import (
    CompleteGoogleSetupSerializer,
    SuccessResponseSerializer,
    UserDetailsSerializer,
)
from ..services.user_bootstrap import UserBootstrapService

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
        """Complete OAuth user setup for all OAuth providers."""
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
                UserBootstrapService.bootstrap_user(
                    user,
                    language=language,
                    timezone_str=timezone_str,
                    scene=scene,
                    email_config=(
                        UserBootstrapService.build_oauth_email_config()
                    ),
                    prompt_description='AI prompt configuration',
                    email_description='Email fetch configuration',
                    email_alias=username,
                )

                logger.info(
                    f"Google user {user.username} completed setup"
                )

            refresh = RefreshToken.for_user(user)

            # Use UserDetailsSerializer to get complete user info,
            # including virtual_email.
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
            error_type = type(e).__name__
            error_message = str(e)
            client_ip = request.META.get('REMOTE_ADDR', 'unknown')
            logger.error(
                f"Failed to complete OAuth setup - "
                f"IP: {client_ip}, "
                f"User: {user.username}, "
                f"Email: {user.email}, "
                f"Error: {error_type}: {error_message}",
                exc_info=True,
                extra={
                    'client_ip': client_ip,
                    'user_id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'exception_type': error_type,
                    'exception_message': error_message,
                    'endpoint': 'oauth_complete_setup',
                    'error_type': 'oauth_setup_failed',
                }
            )

            # Determine error code based on exception type
            if isinstance(e, ValueError):
                error_code = 'VALIDATION_ERROR'
            elif 'UNIQUE constraint' in error_message:
                error_code = 'DUPLICATE_ENTRY'
            elif (
                'EmailAlias' in error_type or
                'email' in error_message.lower()
            ):
                error_code = 'EMAIL_ALIAS_ERROR'
            else:
                error_code = 'OAUTH_SETUP_FAILED'

            return Response(
                {
                    'success': False,
                    'error': _('Failed to complete setup'),
                    'error_detail': f'{error_type}: {error_message}',
                    'error_code': error_code
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
        try:
            user = request.user
            client_ip = request.META.get('REMOTE_ADDR', 'unknown')

            if user and user.is_authenticated:
                try:
                    refresh = RefreshToken.for_user(user)
                    access_token = str(refresh.access_token)
                    refresh_token = str(refresh)

                    redirect_url = (
                        f"{settings.FRONTEND_URL}/auth/oauth/callback"
                        f"?access_token={access_token}"
                        f"&refresh_token={refresh_token}"
                    )

                    logger.info(
                        f"OAuth redirect: {user.email} "
                        f"(username: {user.username}) "
                        f"→ frontend with JWT tokens (IP: {client_ip})"
                    )

                    return redirect(redirect_url)
                except Exception as e:
                    error_type = type(e).__name__
                    error_message = str(e)
                    logger.error(
                        f"Failed to generate JWT tokens for OAuth user - "
                        f"IP: {client_ip}, "
                        f"User: {user.email}, "
                        f"Error: {error_type}: {error_message}",
                        exc_info=True
                    )
                    # Redirect to frontend error page with error info
                    error_url = (
                        f"{settings.FRONTEND_URL}/auth/oauth/error"
                        f"?error=token_generation_failed"
                        f"&message={error_message}"
                    )
                    return redirect(error_url)

            logger.warning(
                f"OAuth callback: user not authenticated "
                f"(IP: {client_ip}), redirecting to error page"
            )
            # Redirect to frontend error page
            error_url = (
                f"{settings.FRONTEND_URL}/auth/oauth/error"
                f"?error=authentication_failed"
            )
            return redirect(error_url)

        except Exception as e:
            error_type = type(e).__name__
            error_message = str(e)
            client_ip = request.META.get('REMOTE_ADDR', 'unknown')
            logger.error(
                f"Unexpected error in OAuth callback redirect - "
                f"IP: {client_ip}, "
                f"Error: {error_type}: {error_message}",
                exc_info=True
            )
            # Redirect to frontend error page
            error_url = (
                f"{settings.FRONTEND_URL}/auth/oauth/error"
                f"?error=unexpected_error"
                f"&message={error_message}"
            )
            return redirect(error_url)
