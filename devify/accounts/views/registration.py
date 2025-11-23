"""
Registration-related views.

Handles user registration flow including email verification,
token validation, and registration completion.
"""

import logging

from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from threadline.models import EmailAlias, Settings
from threadline.utils.prompt_config_manager import PromptConfigManager

from ..models import Profile
from ..serializers import (
    AuthTokenResponseSerializer,
    CompleteRegistrationSerializer,
    SceneSerializer,
    SendRegistrationEmailSerializer,
    SuccessResponseSerializer,
    TokenVerificationResponseSerializer,
    UsernameAvailabilityResponseSerializer,
    VirtualEmailUsernameSerializer,
)
from ..services import (
    RegistrationEmailService,
    RegistrationService,
)

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
                f"Email send attempt result: {success} for {email} "
                f"(language: {language})"
            )

            if success:
                logger.info(
                    f"Sent registration email to {email} "
                    f"(language: {language})"
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
                logger.error(
                    f"Registration email send failed for {email} "
                    f"(language: {language}, token: {token[:10]}...)",
                    extra={
                        'email': email,
                        'language': language,
                        'token_prefix': token[:10] if token else None,
                    }
                )
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
                f"Error in registration email flow for {email} "
                f"(language: {language}): {type(e).__name__}: {str(e)}",
                exc_info=True,
                extra={
                    'email': email,
                    'language': language,
                    'exception_type': type(e).__name__,
                    'exception_message': str(e),
                }
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
