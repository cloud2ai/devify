import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from django.views import View

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from threadline.models import EmailAlias, Settings
from threadline.utils.prompt_config_manager import PromptConfigManager

from .models import Profile
from .serializers import (
    AuthTokenResponseSerializer,
    CompleteGoogleSetupSerializer,
    CompleteRegistrationSerializer,
    SceneSerializer,
    SendRegistrationEmailSerializer,
    SuccessResponseSerializer,
    TokenVerificationResponseSerializer,
    UsernameAvailabilityResponseSerializer,
    VirtualEmailUsernameSerializer,
)
from .services import RegistrationEmailService, RegistrationService

logger = logging.getLogger(__name__)


class SendRegistrationEmailView(APIView):
    """
    Send registration email with verification link.

    This is the first step of email registration flow.
    User provides email, system sends verification link.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['auth'],
        summary=_("Send registration email"),
        request=SendRegistrationEmailSerializer,
        responses={200: SuccessResponseSerializer}
    )
    def post(self, request):
        """
        Send registration verification email.
        """
        serializer = SendRegistrationEmailSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'errors': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        email = serializer.validated_data['email']
        language = request.data.get('language', 'en-US')

        try:
            logger.info(
                f"Starting registration flow for: {email}, "
                f"language: {language}"
            )

            token, profile = (
                RegistrationService.create_registration_token(
                    email,
                    language
                )
            )
            logger.info(
                f"Registration token created for: {email}"
            )

            success = RegistrationEmailService.send_registration_email(
                email,
                token,
                language
            )
            logger.info(
                f"Email send attempt result: {success} for {email}"
            )

            if success:
                logger.info(
                    f"Sent registration email to {email}"
                )
                return Response(
                    {
                        'success': True,
                        'message': _(
                            'Registration email sent successfully'
                        )
                    },
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {
                        'success': False,
                        'error': _(
                            'Failed to send registration email'
                        )
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            logger.error(
                f"Error in registration email flow: {e}",
                exc_info=True
            )
            return Response(
                {
                    'success': False,
                    'error': _('Failed to process registration request')
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VerifyRegistrationTokenView(APIView):
    """
    Verify registration token validity.

    This endpoint is called when user clicks the email link
    to check if the token is still valid.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['auth'],
        summary=_("Verify registration token"),
        parameters=[
            OpenApiParameter(
                name='token',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description=_("Registration verification token")
            )
        ],
        responses={200: TokenVerificationResponseSerializer}
    )
    def get(self, request, token):
        """
        Verify registration token.
        """
        try:
            profile = Profile.objects.select_related('user').get(
                registration_token=token
            )

            is_valid = RegistrationService.is_token_valid(
                token,
                profile.registration_token_expires
            )

            if is_valid:
                return Response(
                    {
                        'valid': True,
                        'email': profile.user.email
                    },
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {
                        'valid': False,
                        'error': _('Token has expired')
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        except Profile.DoesNotExist:
            return Response(
                {
                    'valid': False,
                    'error': _('Invalid token')
                },
                status=status.HTTP_404_NOT_FOUND
            )


class CompleteRegistrationView(APIView):
    """
    Complete user registration.

    This is the final step where user sets password,
    virtual email, and preferences.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['auth'],
        summary=_("Complete registration"),
        request=CompleteRegistrationSerializer,
        responses={200: AuthTokenResponseSerializer}
    )
    def post(self, request):
        """
        Complete user registration.
        """
        serializer = CompleteRegistrationSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'errors': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        token = serializer.validated_data['token']

        try:
            profile = Profile.objects.select_related('user').get(
                registration_token=token
            )
        except Profile.DoesNotExist:
            return Response(
                {
                    'success': False,
                    'error': _('Invalid registration token')
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if not RegistrationService.is_token_valid(
            token,
            profile.registration_token_expires
        ):
            return Response(
                {
                    'success': False,
                    'error': _('Registration token has expired')
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        email = profile.user.email
        password = serializer.validated_data['password']
        username = serializer.validated_data['virtual_email_username']
        scene = serializer.validated_data['scene']
        language = serializer.validated_data['language']
        timezone_str = serializer.validated_data['timezone']

        try:
            profile.user.delete()

            user = RegistrationService.create_user_with_config(
                email=email,
                password=password,
                username=username,
                scene=scene,
                language=language,
                timezone_str=timezone_str
            )

            refresh = RefreshToken.for_user(user)

            logger.info(
                f"User {user.username} completed registration"
            )

            return Response(
                {
                    'success': True,
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                    'user': {
                        'id': user.id,
                        'email': user.email,
                        'username': user.username,
                    }
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(
                f"Failed to complete registration: {e}",
                exc_info=True
            )
            return Response(
                {
                    'success': False,
                    'error': _('Failed to complete registration')
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CheckVirtualEmailUsernameView(APIView):
    """
    Check virtual email username availability.

    This is a helper endpoint for real-time username validation
    in the registration form.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['auth'],
        summary=_("Check username availability"),
        parameters=[
            OpenApiParameter(
                name='username',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description=_("Username to check")
            )
        ],
        responses={200: UsernameAvailabilityResponseSerializer}
    )
    def get(self, request, username):
        """
        Check username availability.
        """
        serializer = VirtualEmailUsernameSerializer(
            data={'username': username}
        )

        if serializer.is_valid():
            return Response(
                {
                    'available': True,
                    'username': serializer.validated_data['username'],
                    'message': _('Username is available')
                },
                status=status.HTTP_200_OK
            )
        else:
            errors = serializer.errors.get('username', [])
            error_message = errors[0] if errors else _(
                'Invalid username'
            )

            return Response(
                {
                    'available': False,
                    'username': username,
                    'message': str(error_message)
                },
                status=status.HTTP_200_OK
            )


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

                logger.info(
                    f"Google user {user.username} completed setup"
                )

            refresh = RefreshToken.for_user(user)

            return Response(
                {
                    'success': True,
                    'message': _('Setup completed successfully'),
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                    'user': {
                        'id': user.id,
                        'email': user.email,
                        'username': user.username,
                        'registration_completed': True
                    }
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


class GetAvailableScenesView(APIView):
    """
    Get available usage scenes.

    Returns list of available scenes with names and descriptions
    in the requested language.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['auth'],
        summary=_("Get available scenes"),
        parameters=[
            OpenApiParameter(
                name='language',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description=_("Language code (e.g., 'zh-CN', 'en-US')"),
                required=False
            )
        ],
        responses={200: SceneSerializer(many=True)}
    )
    def get(self, request):
        """
        Get list of available scenes.
        """
        language = request.query_params.get('language', 'en-US')

        try:
            config_manager = PromptConfigManager()

            if not config_manager.yaml_config:
                return Response(
                    {
                        'success': False,
                        'error': _(
                            'Configuration not available'
                        )
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            scene_config = config_manager.yaml_config.get(
                'scene_config',
                {}
            )

            scenes = []
            for scene_key, scene_data in scene_config.items():
                try:
                    scene_info = config_manager.get_scene_config(
                        scene_key,
                        language
                    )
                    scenes.append({
                        'key': scene_key,
                        'name': scene_info.get('name', scene_key),
                        'description': scene_info.get('description', '')
                    })
                except KeyError as e:
                    logger.warning(
                        f"Scene {scene_key} not available "
                        f"for language {language}: {e}"
                    )
                    continue

            if not scenes:
                return Response(
                    {
                        'success': False,
                        'error': _(
                            'No scenes available for the requested language'
                        )
                    },
                    status=status.HTTP_404_NOT_FOUND
                )

            serializer = SceneSerializer(scenes, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(
                f"Failed to get available scenes: {e}",
                exc_info=True
            )
            return Response(
                {
                    'success': False,
                    'error': _('Failed to retrieve available scenes')
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
