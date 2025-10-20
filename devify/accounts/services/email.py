"""
Email service for sending registration emails.

This service handles sending HTML emails for user registration,
supporting multiple languages with proper internationalization.
"""

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _


logger = logging.getLogger(__name__)


class RegistrationEmailService:
    """
    Service class for sending registration-related emails.

    Handles email template rendering, multi-language support,
    and email delivery.
    """

    @staticmethod
    def send_registration_email(email, token, language='en-US'):
        """
        Send registration email with verification link.

        Args:
            email: Recipient email address
            token: Registration verification token
            language: Language code ('en-US', 'zh-CN')

        Returns:
            bool: True if email sent successfully, False otherwise

        Example:
            success = RegistrationEmailService.send_registration_email(
                'user@example.com',
                'abc123token',
                'zh-CN'
            )
        """
        try:
            template_map = {
                'zh-CN': (
                    'emails/registration/registration_email_zh.html'
                ),
                'en-US': (
                    'emails/registration/registration_email_en.html'
                ),
            }
            template = template_map.get(
                language,
                template_map['en-US']
            )

            registration_url = (
                f"{settings.FRONTEND_URL}/register/complete/{token}"
            )

            html_content = render_to_string(template, {
                'registration_url': registration_url,
                'token': token,
            })

            subject_map = {
                'zh-CN': _('Complete Your AimyChats Registration'),
                'en-US': _('Complete Your AimyChats Registration'),
            }
            subject = str(subject_map.get(language, subject_map['en-US']))

            text_content = str(_(
                'Please complete your registration by visiting: '
                '%(url)s'
            ) % {'url': registration_url})

            from_email = (
                settings.EMAIL_HOST_USER
                if settings.EMAIL_HOST_USER
                else settings.DEFAULT_FROM_EMAIL
            )

            email_message = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=from_email,
                to=[email]
            )
            email_message.attach_alternative(html_content, "text/html")

            email_message.send()

            logger.info(
                f"Sent registration email to {email} "
                f"(language: {language})"
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to send registration email to {email}: {e}"
            )
            return False


class PasswordResetEmailService:
    """
    Service class for sending password reset emails.

    Handles email template rendering, multi-language support,
    and email delivery for password reset functionality.
    """

    @staticmethod
    def send_password_reset_email(email, uid, token, language='en-US'):
        """
        Send password reset email with verification link.

        Args:
            email: Recipient email address
            uid: User ID encoded in base64
            token: Password reset token from Django's token generator
            language: Language code from user profile ('en-US', 'zh-CN')

        Returns:
            bool: True if email sent successfully, False otherwise

        Example:
            success = PasswordResetEmailService.send_password_reset_email(
                'user@example.com',
                'MQ',
                'abc123-xyz789',
                'zh-CN'
            )
        """
        try:
            template_map = {
                'zh-CN': (
                    'emails/password_reset/password_reset_email_zh.html'
                ),
                'en-US': (
                    'emails/password_reset/password_reset_email_en.html'
                ),
            }
            template = template_map.get(
                language,
                template_map['en-US']
            )

            reset_url = (
                f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}/"
            )

            html_content = render_to_string(template, {
                'reset_url': reset_url,
                'uid': uid,
                'token': token,
            })

            subject_map = {
                'zh-CN': _('Reset Your AimyChats Password'),
                'en-US': _('Reset Your AimyChats Password'),
            }
            subject = str(subject_map.get(language, subject_map['en-US']))

            text_content = str(_(
                'Please reset your password by visiting: '
                '%(url)s'
            ) % {'url': reset_url})

            from_email = (
                settings.EMAIL_HOST_USER
                if settings.EMAIL_HOST_USER
                else settings.DEFAULT_FROM_EMAIL
            )

            email_message = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=from_email,
                to=[email]
            )
            email_message.attach_alternative(html_content, "text/html")

            email_message.send()

            logger.info(
                f"Sent password reset email to {email} "
                f"(language: {language})"
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to send password reset email to {email}: {e}"
            )
            return False
