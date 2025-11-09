"""
Billing module Celery tasks
"""
import logging

from celery import shared_task

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils import timezone
from django.utils import translation
from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task
def send_payment_failure_notification(
    user_id: int,
    attempt_count: int = 1,
    failure_reason: str = "Unknown error"
):
    """
    Send email notification when subscription payment fails

    Args:
        user_id: User ID
        attempt_count: Current retry attempt (1-4)
        failure_reason: Stripe error message

    Returns:
        dict: Notification details including user_id, email, and sent_at

    Raises:
        User.DoesNotExist: If user not found
        Exception: If email sending fails
    """
    try:
        user = User.objects.select_related('profile').get(id=user_id)
        user_language = _get_user_language(user)
        billing_url = f"{settings.FRONTEND_URL}/billing"

        translation.activate(user_language)
        try:
            if attempt_count >= 3:
                subject = _("⚠️ Payment Failed - Action Required")
                urgency = "urgent"
                message = _(
                    "Your subscription payment has failed "
                    "%(attempt_count)s times.\n"
                    "Reason: %(failure_reason)s\n\n"
                    "Please update your payment method immediately "
                    "to avoid service interruption.\n\n"
                    "Update payment method: %(billing_url)s"
                ) % {
                    'attempt_count': attempt_count,
                    'failure_reason': failure_reason,
                    'billing_url': billing_url,
                }
            else:
                subject = _("Payment Failed - Automatic Retry Scheduled")
                urgency = "normal"
                message = _(
                    "Your subscription payment failed "
                    "(Attempt %(attempt_count)s).\n"
                    "Reason: %(failure_reason)s\n\n"
                    "Stripe will retry automatically in the next few days.\n"
                    "If the issue persists, "
                    "please update your payment method.\n\n"
                    "Manage subscription: %(billing_url)s"
                ) % {
                    'attempt_count': attempt_count,
                    'failure_reason': failure_reason,
                    'billing_url': billing_url,
                }

            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        finally:
            translation.deactivate()

        logger.info(
            f"Sent payment failure notification to user {user_id} "
            f"(attempt {attempt_count}, urgency: {urgency}, "
            f"language: {user_language})"
        )

        return {
            'user_id': user_id,
            'email': user.email,
            'attempt_count': attempt_count,
            'urgency': urgency,
            'language': user_language,
            'sent_at': timezone.now().isoformat()
        }

    except User.DoesNotExist:
        error_msg = (
            f"User {user_id} not found for payment failure notification"
        )
        logger.error(error_msg)
        raise

    except Exception as e:
        logger.error(
            f"Failed to send payment failure notification "
            f"to user {user_id}: {e}",
            exc_info=True
        )
        raise


@shared_task
def send_payment_success_notification(user_id: int, amount: float):
    """
    Send email notification when payment succeeds after failure

    Args:
        user_id: User ID
        amount: Payment amount in dollars

    Returns:
        dict: Notification details if successful, None if failed
    """
    try:
        user = User.objects.select_related('profile').get(id=user_id)
        user_language = _get_user_language(user)
        billing_url = f"{settings.FRONTEND_URL}/billing"

        translation.activate(user_language)
        try:
            subject = _("✅ Payment Successful")
            message = _(
                "Your subscription payment of $%(amount).2f was successful.\n\n"
                "Thank you for your continued subscription!\n\n"
                "View subscription: %(billing_url)s"
            ) % {
                'amount': amount,
                'billing_url': billing_url,
            }

            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
        finally:
            translation.deactivate()

        logger.info(
            f"Sent payment success notification to user {user_id} "
            f"(language: {user_language})"
        )

        return {
            'user_id': user_id,
            'email': user.email,
            'amount': amount,
            'language': user_language,
            'sent_at': timezone.now().isoformat()
        }

    except Exception as e:
        logger.error(
            f"Failed to send payment success notification: {e}",
            exc_info=True
        )
        return None


def _get_user_language(user) -> str:
    """
    Get user's preferred language from profile

    Args:
        user: Django User instance with profile relationship loaded

    Returns:
        str: Language code (e.g., 'en-US', 'zh-CN', 'es')
             Defaults to 'en-US' if profile not found
    """
    try:
        if hasattr(user, 'profile') and user.profile:
            language = user.profile.language
            return _normalize_language_code(language)
        return 'en-US'
    except Exception as e:
        logger.warning(
            f"Failed to get language for user {user.id}: {e}, "
            f"using default 'en-US'"
        )
        return 'en-US'


def _normalize_language_code(language_code: str) -> str:
    """
    Normalize language code for Django i18n

    Args:
        language_code: Language code from Profile (e.g., 'en-US', 'zh-CN')

    Returns:
        str: Normalized language code compatible with Django

    Examples:
        'en-US' -> 'en'
        'zh-CN' -> 'zh-hans'
        'es' -> 'es'
    """
    language_map = {
        'en-US': 'en',
        'zh-CN': 'zh-hans',
        'es': 'es',
    }
    return language_map.get(language_code, 'en')
