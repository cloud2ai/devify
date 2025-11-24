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
                f"Starting registration flow - "
                f"Email: {email}, "
                f"Language: {language}",
                extra={
                    'email': email,
                    'language': language,
                    'endpoint': 'register_send_email',
                }
            )

            token, profile = (
                RegistrationService.create_registration_token(
                    email,
                    language
                )
            )
            token_prefix = token[:10] if token else None
            logger.info(
                f"Registration token created - "
                f"Email: {email}, "
                f"Token prefix: {token_prefix}...",
                extra={
                    'email': email,
                    'token_prefix': token_prefix,
                    'endpoint': 'register_send_email',
                }
            )

            success = RegistrationEmailService.send_registration_email(
                email,
                token,
                language
            )

            if success:
                logger.info(
                    f"Sent registration email successfully - "
                    f"Email: {email}, "
                    f"Language: {language}",
                    extra={
                        'email': email,
                        'language': language,
                        'endpoint': 'register_send_email',
                    }
                )
                return Response(
                    {
                        'success': True,
                        'message': _('Registration email sent successfully')
                    },
                    status=status.HTTP_200_OK
                )
            else:
                logger.error(
                    f"Registration email send failed - "
                    f"Email: {email}, "
                    f"Language: {language}, "
                    f"Token prefix: {token_prefix}...",
                    extra={
                        'email': email,
                        'language': language,
                        'token_prefix': token_prefix,
                        'endpoint': 'register_send_email',
                        'error_type': 'email_send_failed',
                    }
                )
                return Response(
                    {
                        'success': False,
                        'error': _('Failed to send registration email'),
                        'error_detail': (
                            'Email service returned failure. '
                            'Check email configuration and SMTP settings.'
                        ),
                        'error_code': 'EMAIL_SEND_FAILED'
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            error_type = type(e).__name__
            error_message = str(e)
            logger.error(
                f"Error in registration email flow - "
                f"Email: {email}, "
                f"Language: {language}, "
                f"Error: {error_type}: {error_message}",
                exc_info=True,
                extra={
                    'email': email,
                    'language': language,
                    'exception_type': error_type,
                    'exception_message': error_message,
                    'endpoint': 'register_send_email',
                    'error_type': 'registration_flow_error',
                }
            )
            return Response(
                {
                    'success': False,
                    'error': _('Failed to process registration request'),
                    'error_detail': f'{error_type}: {error_message}',
                    'error_code': 'REGISTRATION_FLOW_ERROR'
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
        client_ip = request.META.get('REMOTE_ADDR', 'unknown')
        token_prefix = token[:10] if len(token) > 10 else token

        try:
            profile = Profile.objects.select_related('user').get(
                registration_token=token
            )

            is_valid = RegistrationService.is_token_valid(
                token,
                profile.registration_token_expires
            )

            if is_valid:
                logger.info(
                    f"Token verification successful - "
                    f"IP: {client_ip}, "
                    f"Token prefix: {token_prefix}..., "
                    f"Email: {profile.user.email}",
                    extra={
                        'client_ip': client_ip,
                        'token_prefix': token_prefix,
                        'email': profile.user.email,
                        'endpoint': 'register_verify_token',
                    }
                )
                return Response(
                    {
                        'valid': True,
                        'email': profile.user.email
                    },
                    status=status.HTTP_200_OK
                )
            else:
                logger.warning(
                    f"Token verification failed: Token expired - "
                    f"IP: {client_ip}, "
                    f"Token prefix: {token_prefix}..., "
                    f"Email: {profile.user.email}, "
                    f"Expires at: {profile.registration_token_expires}",
                    extra={
                        'client_ip': client_ip,
                        'token_prefix': token_prefix,
                        'email': profile.user.email,
                        'token_expires': str(
                            profile.registration_token_expires
                        ),
                        'endpoint': 'register_verify_token',
                        'error_type': 'token_expired',
                    }
                )
                return Response(
                    {
                        'valid': False,
                        'error': _('Token has expired')
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        except Profile.DoesNotExist:
            logger.warning(
                f"Token verification failed: Invalid token - "
                f"IP: {client_ip}, "
                f"Token prefix: {token_prefix}...",
                extra={
                    'client_ip': client_ip,
                    'token_prefix': token_prefix,
                    'endpoint': 'register_verify_token',
                    'error_type': 'invalid_token',
                }
            )
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
        client_ip = request.META.get('REMOTE_ADDR', 'unknown')
        request_data = request.data.copy()

        # Mask sensitive data for logging
        safe_request_data = request_data.copy()
        if 'password' in safe_request_data:
            safe_request_data['password'] = '***'
        if 'token' in safe_request_data:
            token_value = safe_request_data.get('token', '')
            if token_value:
                safe_request_data['token'] = (
                    f"{token_value[:10]}..."
                    if len(token_value) > 10
                    else "***"
                )

        serializer = CompleteRegistrationSerializer(data=request.data)

        if not serializer.is_valid():
            logger.warning(
                f"Registration completion validation failed - "
                f"IP: {client_ip}, "
                f"Request data: {safe_request_data}, "
                f"Validation errors: {serializer.errors}",
                extra={
                    'client_ip': client_ip,
                    'request_data': safe_request_data,
                    'validation_errors': serializer.errors,
                    'endpoint': 'register_complete',
                }
            )
            return Response(
                {
                    'success': False,
                    'errors': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        token = serializer.validated_data['token']
        token_prefix = (
            token[:10]
            if len(token) > 10
            else token
        )

        try:
            profile = Profile.objects.select_related('user').get(
                registration_token=token
            )
        except Profile.DoesNotExist:
            username = safe_request_data.get('virtual_email_username', 'N/A')
            logger.warning(
                f"Registration completion failed: Invalid token - "
                f"IP: {client_ip}, "
                f"Token prefix: {token_prefix}..., "
                f"Username: {username}",
                extra={
                    'client_ip': client_ip,
                    'token_prefix': token_prefix,
                    'username': username,
                    'endpoint': 'register_complete',
                    'error_type': 'invalid_token',
                }
            )
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
            logger.warning(
                f"Registration completion failed: Token expired - "
                f"IP: {client_ip}, "
                f"Token prefix: {token_prefix}..., "
                f"Email: {profile.user.email}, "
                f"Expires at: {profile.registration_token_expires}",
                extra={
                    'client_ip': client_ip,
                    'token_prefix': token_prefix,
                    'email': profile.user.email,
                    'token_expires': str(profile.registration_token_expires),
                    'endpoint': 'register_complete',
                    'error_type': 'token_expired',
                }
            )
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

        logger.info(
            f"Starting registration completion - "
            f"IP: {client_ip}, "
            f"Email: {email}, "
            f"Username: {username}, "
            f"Scene: {scene}, "
            f"Language: {language}, "
            f"Timezone: {timezone_str}",
            extra={
                'client_ip': client_ip,
                'email': email,
                'username': username,
                'scene': scene,
                'language': language,
                'timezone': timezone_str,
                'endpoint': 'register_complete',
            }
        )

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
                f"User {user.username} (ID: {user.id}, Email: {user.email}) "
                f"completed registration successfully - IP: {client_ip}",
                extra={
                    'user_id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'client_ip': client_ip,
                    'endpoint': 'register_complete',
                }
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
            error_type = type(e).__name__
            error_message = str(e)
            logger.error(
                f"Failed to complete registration - "
                f"IP: {client_ip}, "
                f"Email: {email}, "
                f"Username: {username}, "
                f"Error: {error_type}: {error_message}",
                exc_info=True,
                extra={
                    'client_ip': client_ip,
                    'email': email,
                    'username': username,
                    'scene': scene,
                    'language': language,
                    'timezone': timezone_str,
                    'exception_type': error_type,
                    'exception_message': error_message,
                    'endpoint': 'register_complete',
                    'error_type': 'registration_failed',
                }
            )

            # Determine error code based on exception type
            if isinstance(e, ValueError):
                error_code = 'VALIDATION_ERROR'
            elif isinstance(e, User.DoesNotExist):
                error_code = 'USER_NOT_FOUND'
            else:
                error_code = 'REGISTRATION_FAILED'

            return Response(
                {
                    'success': False,
                    'error': _('Failed to complete registration'),
                    'error_detail': f'{error_type}: {error_message}',
                    'error_code': error_code
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
