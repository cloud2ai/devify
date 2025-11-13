"""
Billing periodic tasks for Celery Beat

Tasks for automatic credit renewal and subscription management.
"""

import logging

from celery import shared_task
from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils import translation

from .models import Subscription, UserCredits
from .services.credits_service import CreditsService

logger = logging.getLogger(__name__)


@shared_task(name='billing.tasks.renew_expired_credits')
def renew_expired_credits():
    """
    Automatically renew credits for users with expired periods.

    Runs daily to check for expired credit periods and reset them
    based on the user's active subscription plan.

    For Free Plan users: Resets to free tier credits (no payment required)
    For Paid Plan users: Only if subscription is still active
    """
    now = timezone.now()

    # Find all users with expired credit periods and active subscriptions
    expired_credits = UserCredits.objects.filter(
        period_end__lte=now,
        is_active=True,
        subscription__isnull=False,
        subscription__status='active'
    ).select_related('user', 'subscription', 'subscription__plan')

    renewed_count = 0
    failed_count = 0

    logger.info(
        f"Starting credit renewal check. "
        f"Found {expired_credits.count()} expired credit periods."
    )

    for credits in expired_credits:
        try:
            user_id = credits.user.id
            plan_name = credits.subscription.plan.name

            # Reset credits for new period
            CreditsService.reset_period_credits(user_id)

            renewed_count += 1
            logger.info(
                f"Renewed credits for user {credits.user.username} "
                f"(Plan: {plan_name})"
            )

        except Exception as e:
            failed_count += 1
            logger.error(
                f"Failed to renew credits for user "
                f"{credits.user.username}: {e}",
                exc_info=True
            )

    logger.info(
        f"Credit renewal completed. "
        f"Renewed: {renewed_count}, Failed: {failed_count}"
    )

    return {
        'renewed': renewed_count,
        'failed': failed_count,
        'total_checked': expired_credits.count()
    }


@shared_task(name='billing.tasks.downgrade_failed_paid_subscriptions')
def downgrade_failed_paid_subscriptions():
    """
    Downgrade paid subscriptions to Free Plan when payment fails.

    Checks for subscriptions in 'past_due' status for more than 7 days.
    If payment is still not received, automatically downgrades to Free Plan.

    Process:
    1. Find subscriptions: status='past_due' AND past_due > 7 days
    2. Cancel Stripe subscription
    3. Create new Free Plan subscription
    4. Reset user credits to Free Plan limits

    Note: This ensures users don't lose access completely,
          they just get downgraded to free tier.
    """
    from datetime import timedelta
    from billing.models import Plan, PaymentProvider

    now = timezone.now()
    grace_period_days = 7
    cutoff_time = now - timedelta(days=grace_period_days)

    # Find paid subscriptions that are past_due for too long
    past_due_subs = Subscription.objects.filter(
        status='past_due',
        updated_at__lte=cutoff_time,
        plan__slug__in=['starter', 'standard', 'pro']
    ).select_related('user', 'plan')

    downgraded_count = 0
    failed_count = 0

    logger.info(
        f"Checking for past_due paid subscriptions. "
        f"Found {past_due_subs.count()} candidates."
    )

    for subscription in past_due_subs:
        try:
            user = subscription.user
            old_plan = subscription.plan.name

            # Cancel old subscription
            subscription.status = 'canceled'
            subscription.auto_renew = False
            subscription.save()

            # Create Free Plan subscription
            free_plan = Plan.objects.get(slug='free')
            payment_provider = PaymentProvider.objects.get(name='stripe')

            period_days = free_plan.metadata.get('period_days', 30)
            period_end = now + timedelta(days=period_days)
            base_credits = free_plan.metadata.get('credits_per_period', 10)

            new_subscription = Subscription.objects.create(
                user=user,
                plan=free_plan,
                provider=payment_provider,
                status='active',
                current_period_start=now,
                current_period_end=period_end,
                auto_renew=False
            )

            # Update user credits
            user_credits = UserCredits.objects.get(user=user)
            user_credits.subscription = new_subscription
            user_credits.base_credits = base_credits
            user_credits.consumed_credits = 0
            user_credits.period_start = now
            user_credits.period_end = period_end
            user_credits.save()

            downgraded_count += 1
            logger.info(
                f"Downgraded user {user.username} from {old_plan} "
                f"to Free Plan (payment failed)"
            )

        except Exception as e:
            failed_count += 1
            logger.error(
                f"Failed to downgrade subscription for "
                f"{subscription.user.username}: {e}",
                exc_info=True
            )

    logger.info(
        f"Paid subscription downgrade completed. "
        f"Downgraded: {downgraded_count}, Failed: {failed_count}"
    )

    return {
        'downgraded': downgraded_count,
        'failed': failed_count,
        'total_checked': past_due_subs.count()
    }


def _get_user_language(user):
    """
    Get user's preferred language from profile
    """
    try:
        if hasattr(user, 'profile') and user.profile:
            return user.profile.language or 'en-US'
    except Exception:
        pass
    return 'en-US'


@shared_task(name='billing.tasks.send_payment_success_notification')
def send_payment_success_notification(user_id, amount):
    """
    Send email notification when payment succeeds

    Args:
        user_id: User ID
        amount: Payment amount in dollars
    """
    try:
        user = User.objects.select_related('profile').get(id=user_id)
        user_language = _get_user_language(user)
        billing_url = f"{settings.FRONTEND_URL}/billing"

        translation.activate(user_language)
        try:
            subject = translation.gettext('Payment Successful')
            message = translation.gettext(
                'Your payment of ${amount} has been processed successfully. '
                'Thank you for your subscription!'
            ).format(amount=amount)

            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )

            logger.info(
                f"Payment success notification sent to {user.email} "
                f"(amount: ${amount})"
            )

        finally:
            translation.deactivate()

    except User.DoesNotExist:
        logger.error(f"User {user_id} not found for payment notification")
    except Exception as e:
        logger.error(
            f"Failed to send payment success notification to "
            f"user {user_id}: {e}",
            exc_info=True
        )


@shared_task(name='billing.tasks.send_payment_failure_notification')
def send_payment_failure_notification(
    user_id,
    attempt_count,
    failure_reason
):
    """
    Send email notification when payment fails

    Args:
        user_id: User ID
        attempt_count: Number of payment attempts
        failure_reason: Reason for payment failure
    """
    try:
        user = User.objects.select_related('profile').get(id=user_id)
        user_language = _get_user_language(user)
        billing_url = f"{settings.FRONTEND_URL}/billing"

        translation.activate(user_language)
        try:
            subject = translation.gettext('Payment Failed - Action Required')
            message = translation.gettext(
                'We were unable to process your payment (Attempt {attempt}). '
                'Reason: {reason}. '
                'Please update your payment method at {url} to continue '
                'your subscription.'
            ).format(
                attempt=attempt_count,
                reason=failure_reason,
                url=billing_url
            )

            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )

            logger.info(
                f"Payment failure notification sent to {user.email} "
                f"(attempt: {attempt_count})"
            )

        finally:
            translation.deactivate()

    except User.DoesNotExist:
        logger.error(f"User {user_id} not found for payment notification")
    except Exception as e:
        logger.error(
            f"Failed to send payment failure notification to "
            f"user {user_id}: {e}",
            exc_info=True
        )
