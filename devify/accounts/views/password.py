"""
Password-related views.

Handles password reset functionality including sending reset emails
and confirming password resets.
"""

import logging
import re

from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt

from drf_spectacular.utils import extend_schema

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ..serializers import (
    CustomPasswordResetSerializer,
    SuccessResponseSerializer,
)
from ..services import PasswordResetEmailService

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class SendPasswordResetEmailView(APIView):
    """
    Send password reset email with verification link.

    This endpoint is used for both:
    1. Forgot password (unauthenticated users provide email)
    2. Change password (authenticated users, email from request.user)

    Only email-registered users can use this feature.
    OAuth users will be rejected.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['auth'],
        summary=_("Send password reset email"),
        request=CustomPasswordResetSerializer,
        responses={200: SuccessResponseSerializer}
    )
    def post(self, request):
        """
        Send password reset verification email.
        """
        if request.user.is_authenticated:
            email = request.user.email
            user = request.user

            if not user.has_usable_password():
                return Response(
                    {
                        'success': False,
                        'error': _(
                            'OAuth users cannot reset password. '
                            'Please login with your OAuth provider.'
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            serializer = CustomPasswordResetSerializer(data=request.data)

            if not serializer.is_valid():
                return Response(
                    {
                        'success': False,
                        'errors': serializer.errors
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            email = serializer.validated_data['email']
            user = User.objects.get(email=email)

        try:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)

            language = user.profile.language

            success = PasswordResetEmailService.send_password_reset_email(
                email=email,
                uid=uid,
                token=token,
                language=language
            )

            if success:
                logger.info(
                    f"Sent password reset email to {email}"
                )
                return Response(
                    {
                        'success': True,
                        'message': _(
                            'Password reset email sent successfully'
                        )
                    },
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {
                        'success': False,
                        'error': _(
                            'Failed to send password reset email'
                        )
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            logger.error(
                f"Error in password reset email flow: {e}",
                exc_info=True
            )
            return Response(
                {
                    'success': False,
                    'error': _(
                        'Failed to process password reset request'
                    )
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@method_decorator(csrf_exempt, name='dispatch')
class ConfirmPasswordResetView(APIView):
    """
    Confirm password reset with uid, token, and new password.

    This is the final step where user submits new password
    after clicking the link in the email.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['auth'],
        summary=_("Confirm password reset"),
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'uid': {
                        'type': 'string',
                        'description': 'User ID encoded in base64'
                    },
                    'token': {
                        'type': 'string',
                        'description': 'Password reset token'
                    },
                    'new_password1': {
                        'type': 'string',
                        'description': 'New password'
                    },
                    'new_password2': {
                        'type': 'string',
                        'description': 'Confirm new password'
                    }
                },
                'required': [
                    'uid',
                    'token',
                    'new_password1',
                    'new_password2'
                ]
            }
        },
        responses={200: SuccessResponseSerializer}
    )
    def post(self, request):
        """
        Confirm password reset.
        """
        uid = request.data.get('uid')
        token = request.data.get('token')
        # Try all possible field name variations
        new_password1 = (request.data.get('newPassword1') or
                         request.data.get('new_password1') or
                         request.data.get('new_password_1'))
        new_password2 = (request.data.get('newPassword2') or
                         request.data.get('new_password2') or
                         request.data.get('new_password_2'))

        if not all([uid, token, new_password1, new_password2]):
            return Response(
                {
                    'success': False,
                    'error': _('All fields are required')
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if new_password1 != new_password2:
            return Response(
                {
                    'success': False,
                    'error': _('Passwords do not match')
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user_id = urlsafe_base64_decode(uid).decode()
            user = User.objects.get(pk=user_id)
        except (
            TypeError,
            ValueError,
            OverflowError,
            User.DoesNotExist
        ) as e:
            return Response(
                {
                    'success': False,
                    'error': _('Invalid reset link')
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if not default_token_generator.check_token(user, token):
            return Response(
                {
                    'success': False,
                    'error': _(
                        'Invalid or expired reset link'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(new_password1) < 8:
            return Response(
                {
                    'success': False,
                    'error': _(
                        'Password must be at least 8 characters long'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(new_password1) > 32:
            return Response(
                {
                    'success': False,
                    'error': _('Password cannot exceed 32 characters')
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        has_letter = re.search(r'[a-zA-Z]', new_password1)
        has_number = re.search(r'[0-9]', new_password1)

        if not (has_letter and has_number):
            return Response(
                {
                    'success': False,
                    'error': _(
                        'Password must contain both letters and numbers'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user.set_password(new_password1)
            user.save()

            logger.info(
                f"Password reset successful for user: {user.email}"
            )

            return Response(
                {
                    'success': True,
                    'message': _(
                        'Password has been reset successfully'
                    )
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(
                f"Error resetting password for {user.email}: {e}",
                exc_info=True
            )
            return Response(
                {
                    'success': False,
                    'error': _('Failed to reset password')
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
