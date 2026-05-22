"""
Billing periodic tasks for Celery Beat

Tasks for automatic credit renewal and subscription management.
"""

import logging
from uuid import uuid4

from celery import shared_task
from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils import translation

from .models import BillingAuditLog, Subscription, UserCredits
from .serializers import SubscriptionSerializer
from .services.audit_service import queue_billing_audit_event
from .services.credits_service import CreditsService
from .services.payment_record_service import backfill_payment_records
from .services.payment_check.service import PaymentCheckService
from threadline.utils.task_tracer import TaskTracer

logger = logging.getLogger(__name__)


@shared_task(name='billing.tasks.record_billing_audit_event')
def record_billing_audit_event(payload: dict):
    """
    Persist a billing audit event.

    This task is intentionally idempotent via event_key so retries or repeated
    enqueue attempts do not create duplicate records.
    """
    event_key = payload.get('event_key') or str(uuid4())
    defaults = {
        'action_type': payload.get('action_type', ''),
        'source': payload.get('source', 'system'),
        'actor_name': payload.get('actor_name', ''),
        'target_username': payload.get('target_username', ''),
        'resource_type': payload.get('resource_type', ''),
        'resource_id': str(payload.get('resource_id') or ''),
        'ip_address': payload.get('ip_address') or None,
        'user_agent': payload.get('user_agent', '') or '',
        'before_data': payload.get('before_data') or {},
        'after_data': payload.get('after_data') or {},
        'context': payload.get('context') or {},
    }

    actor_id = payload.get('actor_id')
    target_user_id = payload.get('target_user_id')
    if actor_id and User.objects.filter(id=actor_id).exists():
        defaults['actor_id'] = actor_id
    if target_user_id and User.objects.filter(id=target_user_id).exists():
        defaults['target_user_id'] = target_user_id

    audit_log, created = BillingAuditLog.objects.get_or_create(
        event_key=event_key,
        defaults=defaults,
    )

    if not created:
        logger.info(
            'Billing audit event already exists event_key=%s action_type=%s',
            event_key,
            audit_log.action_type,
        )
        return {'created': False, 'id': audit_log.id, 'event_key': event_key}

    logger.info(
        'Recorded billing audit event action_type=%s source=%s event_key=%s',
        audit_log.action_type,
        audit_log.source,
        event_key,
    )
    return {'created': True, 'id': audit_log.id, 'event_key': event_key}


@shared_task(name='billing.tasks.renew_expired_credits')
def renew_expired_credits():
    """
    Automatically renew credits for users with expired periods.

    Runs daily to check for expired credit periods and reset them
    based on the user's active subscription plan.

    For Free Plan users: Resets to free tier credits (no payment required)
    For Paid Plan users: Only if subscription is still active
    """
    tracer = TaskTracer(
        "RENEW_EXPIRED_CREDITS",
        module="billing",
    )
    started_at = timezone.now().isoformat()
    tracer.create_task({
        "status": "starting",
        "started_at": started_at,
    })
    tracer.append_task(
        "TASK_START",
        "Billing credit renewal started",
        {"started_at": started_at},
    )

    try:
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
                before_data = SubscriptionSerializer(
                    credits.subscription
                ).data

                # Reset credits for new period
                CreditsService.reset_period_credits(user_id)
                credits.refresh_from_db()
                after_data = {
                    'subscription': SubscriptionSerializer(
                        credits.subscription
                    ).data if credits.subscription else None,
                    'credits': {
                        'base_credits': credits.base_credits,
                        'bonus_credits': credits.bonus_credits,
                        'consumed_credits': credits.consumed_credits,
                        'period_start': credits.period_start.isoformat(),
                        'period_end': credits.period_end.isoformat(),
                    },
                }
                queue_billing_audit_event(
                    action_type='system.renew_expired_credits',
                    source='system_task',
                    target_user_id=credits.user_id,
                    target_username=credits.user.username,
                    resource_type='subscription',
                    resource_id=credits.subscription_id or '',
                    before_data=before_data,
                    after_data=after_data,
                    context={
                        'plan_slug': credits.subscription.plan.slug,
                        'plan_name': plan_name,
                    },
                )

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
        completed_at = timezone.now().isoformat()
        tracer.append_task(
            "TASK_COMPLETE",
            "Billing credit renewal finished",
            {
                "renewed": renewed_count,
                "failed": failed_count,
                "total_checked": expired_credits.count(),
                "completed_at": completed_at,
            },
        )
        tracer.complete_task({
            'renewed': renewed_count,
            'failed': failed_count,
            'total_checked': expired_credits.count(),
            'completed_at': completed_at
        })

        return {
            'renewed': renewed_count,
            'failed': failed_count,
            'total_checked': expired_credits.count()
        }
    except Exception as exc:
        logger.error(f"Credit renewal task failed: {exc}", exc_info=True)
        tracer.append_task(
            "TASK_ERROR",
            f"Billing credit renewal failed: {exc}",
            {"error": str(exc)},
        )
        tracer.fail_task({"error": str(exc)}, str(exc))
        raise


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
    from billing.models import Plan
    from billing.services.subscription_service import SubscriptionService

    tracer = TaskTracer(
        "DOWNGRADE_FAILED_PAID_SUBSCRIPTIONS",
        module="billing",
    )
    started_at = timezone.now().isoformat()
    tracer.create_task({
        "status": "starting",
        "started_at": started_at,
    })
    tracer.append_task(
        "TASK_START",
        "Billing downgrade task started",
        {"started_at": started_at},
    )

    try:
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
                before_data = SubscriptionSerializer(subscription).data

                # Cancel old subscription
                if subscription.djstripe_subscription:
                    SubscriptionService.cancel_subscription(subscription.id)
                    subscription.refresh_from_db()
                    subscription.status = 'canceled'
                    subscription.auto_renew = False
                    subscription.save(update_fields=['status', 'auto_renew'])
                else:
                    subscription.status = 'canceled'
                    subscription.auto_renew = False
                    subscription.save()

                # Create Free Plan subscription
                free_plan = Plan.objects.get(slug='free')
                payment_provider = (
                    SubscriptionService.get_or_create_payment_provider(
                        'platform'
                    )
                )

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
                # Use CreditsService to handle duplicate records
                user_credits = CreditsService.get_user_credits(user.id)
                user_credits.subscription = new_subscription
                user_credits.base_credits = base_credits
                user_credits.consumed_credits = 0
                user_credits.period_start = now
                user_credits.period_end = period_end
                user_credits.save()

                queue_billing_audit_event(
                    action_type='system.downgrade_failed_paid_subscription',
                    source='system_task',
                    target_user_id=user.id,
                    target_username=user.username,
                    resource_type='subscription',
                    resource_id=new_subscription.id,
                    before_data=before_data,
                    after_data={
                        'subscription': SubscriptionSerializer(
                            new_subscription
                        ).data,
                        'credits': {
                            'base_credits': user_credits.base_credits,
                            'bonus_credits': user_credits.bonus_credits,
                            'consumed_credits': user_credits.consumed_credits,
                            'period_start': user_credits.period_start.isoformat(),
                            'period_end': user_credits.period_end.isoformat(),
                        },
                    },
                    context={
                        'old_plan': old_plan,
                        'new_plan': free_plan.slug,
                        'grace_period_days': grace_period_days,
                    },
                )

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
        completed_at = timezone.now().isoformat()
        tracer.append_task(
            "TASK_COMPLETE",
            "Billing downgrade task finished",
            {
                "downgraded": downgraded_count,
                "failed": failed_count,
                "total_checked": past_due_subs.count(),
                "completed_at": completed_at,
            },
        )
        tracer.complete_task({
            'downgraded': downgraded_count,
            'failed': failed_count,
            'total_checked': past_due_subs.count(),
            'completed_at': completed_at
        })

        return {
            'downgraded': downgraded_count,
            'failed': failed_count,
            'total_checked': past_due_subs.count()
        }
    except Exception as exc:
        logger.error(
            f"Paid subscription downgrade task failed: {exc}",
            exc_info=True
        )
        tracer.append_task(
            "TASK_ERROR",
            f"Billing downgrade task failed: {exc}",
            {"error": str(exc)},
        )
        tracer.fail_task({"error": str(exc)}, str(exc))
        raise


@shared_task(name='billing.tasks.payment_check')
def payment_check(providers=None, mode='auto_fix_safe'):
    """
    Run provider-neutral payment status checks.

    By default this is used by the scheduled beat task and will attempt safe
    repairs only. Manual admin actions can override the mode to report-only or
    auto-fix-safe as needed.
    """
    tracer = TaskTracer(
        'PAYMENT_CHECK',
        module='billing',
    )
    started_at = timezone.now().isoformat()
    tracer.create_task(
        {
            'status': 'starting',
            'started_at': started_at,
            'mode': mode,
            'providers': providers or [],
        }
    )
    tracer.append_task(
        'TASK_START',
        'Payment check started',
        {
            'started_at': started_at,
            'mode': mode,
            'providers': providers or [],
        },
    )

    try:
        result = PaymentCheckService.run(
            providers=providers,
            mode=mode,
            actor_context={
                'source': 'system_task',
                'actor_name': 'system',
            },
        )
        completed_at = timezone.now().isoformat()
        tracer.append_task(
            'TASK_COMPLETE',
            'Payment check finished',
            {
                'completed_at': completed_at,
                'totals': result.get('totals', {}),
            },
        )
        tracer.complete_task(
            {
                'completed_at': completed_at,
                'totals': result.get('totals', {}),
            }
        )
        return result
    except Exception as exc:
        logger.error('Payment check task failed: %s', exc, exc_info=True)
        tracer.append_task(
            'TASK_ERROR',
            f'Payment check failed: {exc}',
            {'error': str(exc)},
        )
        tracer.fail_task({'error': str(exc)}, str(exc))
        raise


@shared_task(name='billing.tasks.payment_record_backfill')
def payment_record_backfill(
    lookback_days=None,
    source='scheduled_task',
    user_id=None,
    providers=None,
):
    """
    Backfill missing successful payment invoice records from Stripe invoices.

    This task is intentionally separate from payment_check because it writes
    historical successful payment ledger entries instead of reconciling
    subscription state.
    """
    tracer = TaskTracer(
        'PAYMENT_RECORD_BACKFILL',
        module='billing',
    )
    started_at = timezone.now().isoformat()
    tracer.create_task(
        {
            'status': 'starting',
            'started_at': started_at,
            'lookback_days': lookback_days,
            'source': source,
            'user_id': user_id,
            'providers': providers,
        }
    )
    tracer.append_task(
        'TASK_START',
        'Successful invoice backfill started',
        {
            'started_at': started_at,
            'lookback_days': lookback_days,
            'source': source,
            'user_id': user_id,
            'providers': providers,
        },
    )

    try:
        result = backfill_payment_records(
            lookback_days=lookback_days,
            user_id=user_id,
            providers=providers,
            source=source,
        )
        completed_at = timezone.now().isoformat()
        tracer.append_task(
            'TASK_COMPLETE',
            'Successful invoice backfill finished',
            {
                'completed_at': completed_at,
                'summary': result,
            },
        )
        tracer.complete_task(
            {
                'completed_at': completed_at,
                'summary': result,
            }
        )
        return result
    except Exception as exc:
        logger.error(
            'Successful invoice backfill task failed: %s', exc, exc_info=True
        )
        tracer.append_task(
            'TASK_ERROR',
            f'Successful invoice backfill failed: {exc}',
            {'error': str(exc)},
        )
        tracer.fail_task({'error': str(exc)}, str(exc))
        raise


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
