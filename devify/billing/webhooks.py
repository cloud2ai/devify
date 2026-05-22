import logging

from django.db import transaction

from djstripe.event_handlers import djstripe_receiver
from djstripe.models import Event
from djstripe.models import Subscription as DjstripeSubscription

from billing.models import Subscription
from billing.serializers import SubscriptionSerializer
from billing.services.audit_service import queue_billing_audit_event
from billing.services.customer_identity import resolve_user_for_customer
from billing.services.credits_service import CreditsService
from billing.services.payment_record_service import (
    upsert_payment_record_from_stripe_invoice,
)
from billing.services.subscription_service import SubscriptionService
from billing.tasks import send_payment_failure_notification
from billing.tasks import send_payment_success_notification

logger = logging.getLogger(__name__)


@djstripe_receiver("customer.subscription.created")
def handle_subscription_created(sender, **kwargs):
    """
    Synchronous webhook handling with robust error handling
    """
    event: Event = kwargs.get("event")
    subscription_id = event.data["object"]["id"]

    logger.info(
        f"[WEBHOOK] Received customer.subscription.created "
        f"for subscription {subscription_id}"
    )

    try:
        with transaction.atomic():
            djstripe_subscription = (
                DjstripeSubscription.objects.get(id=subscription_id)
            )

            # Ensure Customer is linked to Django User before syncing
            customer = djstripe_subscription.customer
            user = resolve_user_for_customer(customer)
            if not user:
                logger.warning(
                    f"No linked user found for Stripe customer {customer.id}, "
                    f"skipping subscription sync"
                )
                return

            SubscriptionService.sync_from_djstripe(
                djstripe_subscription
            )

        subscription = Subscription.objects.filter(
            djstripe_subscription__id=subscription_id
        ).select_related('plan', 'provider').first()
        if subscription:
            queue_billing_audit_event(
                action_type='webhook.subscription.created',
                source='webhook',
                target_user_id=subscription.user_id,
                target_username=subscription.user.username,
                resource_type='subscription',
                resource_id=subscription.id,
                before_data={},
                after_data=SubscriptionSerializer(subscription).data,
                context={
                    'djstripe_subscription_id': djstripe_subscription.id,
                    'status': subscription.status,
                },
            )

        logger.info(
            f"Successfully processed subscription.created: "
            f"{subscription_id}"
        )

    except Exception as e:
        logger.error(
            f"Failed to process subscription.created "
            f"{subscription_id}: {e}",
            exc_info=True
        )
        raise


@djstripe_receiver("customer.subscription.updated")
def handle_subscription_updated(sender, **kwargs):
    """
    Handle subscription update synchronously
    """
    event: Event = kwargs.get("event")
    subscription_id = event.data["object"]["id"]

    logger.info(
        f"[WEBHOOK] Received customer.subscription.updated "
        f"for subscription {subscription_id}"
    )

    try:
        with transaction.atomic():
            djstripe_subscription = (
                DjstripeSubscription.objects.get(id=subscription_id)
            )

            # Ensure Customer is linked to Django User
            customer = djstripe_subscription.customer
            user = resolve_user_for_customer(customer)
            if not user:
                logger.warning(
                    f"No linked user found for Stripe customer {customer.id}"
                )
                return

            SubscriptionService.sync_from_djstripe(
                djstripe_subscription
            )

        subscription = Subscription.objects.filter(
            djstripe_subscription__id=subscription_id
        ).select_related('plan', 'provider').first()
        if subscription:
            queue_billing_audit_event(
                action_type='webhook.subscription.updated',
                source='webhook',
                target_user_id=subscription.user_id,
                target_username=subscription.user.username,
                resource_type='subscription',
                resource_id=subscription.id,
                before_data={},
                after_data=SubscriptionSerializer(subscription).data,
                context={
                    'djstripe_subscription_id': djstripe_subscription.id,
                    'status': subscription.status,
                },
            )

        logger.info(
            f"Successfully processed subscription.updated: "
            f"{subscription_id}"
        )

    except Exception as e:
        logger.error(
            f"Failed to process subscription.updated: {e}",
            exc_info=True
        )
        raise


@djstripe_receiver("customer.subscription.deleted")
def handle_subscription_deleted(sender, **kwargs):
    """
    Handle subscription deletion synchronously
    """
    event: Event = kwargs.get("event")
    subscription_id = event.data["object"]["id"]

    logger.info(
        f"[WEBHOOK] Received customer.subscription.deleted "
        f"for subscription {subscription_id}"
    )

    try:
        subscription_before = Subscription.objects.filter(
            djstripe_subscription__id=subscription_id
        ).select_related('user', 'plan', 'provider').first()

        with transaction.atomic():
            SubscriptionService.handle_cancellation(subscription_id)

        subscription_after = Subscription.objects.filter(
            djstripe_subscription__id=subscription_id
        ).select_related('user', 'plan', 'provider').first()
        if subscription_after:
            queue_billing_audit_event(
                action_type='webhook.subscription.deleted',
                source='webhook',
                target_user_id=subscription_after.user_id,
                target_username=subscription_after.user.username,
                resource_type='subscription',
                resource_id=subscription_after.id,
                before_data=(
                    SubscriptionSerializer(subscription_before).data
                    if subscription_before
                    else {}
                ),
                after_data=(
                    SubscriptionSerializer(subscription_after).data
                    if subscription_after
                    else {}
                ),
                context={
                    'djstripe_subscription_id': subscription_id,
                },
            )

        logger.info(
            f"Successfully processed subscription.deleted: "
            f"{subscription_id}"
        )

    except Exception as e:
        logger.error(
            f"Failed to process subscription.deleted: {e}",
            exc_info=True
        )
        raise


@djstripe_receiver("invoice.payment_succeeded")
def handle_payment_succeeded(sender, **kwargs):
    """
    Handle payment success synchronously

    Updates subscription status from 'past_due' to 'active' if payment
    was previously failing. Credit allocation is handled by subscription
    webhooks automatically.
    """
    event: Event = kwargs.get("event")
    invoice = event.data["object"]
    customer_id = invoice["customer"]
    subscription_id = invoice.get("subscription")
    amount_paid = invoice.get("amount_paid", 0) / 100.0

    try:
        with transaction.atomic():
            logger.info(
                f"Payment succeeded for customer {customer_id}, "
                f"invoice {invoice['id']}, subscription {subscription_id}, "
                f"amount: ${amount_paid:.2f}"
            )

            record_result = upsert_payment_record_from_stripe_invoice(
                invoice,
                source='webhook',
                event_type='invoice.payment_succeeded',
                status='succeeded',
            )
            if record_result.skipped:
                logger.warning(
                    'Skipped payment record sync for invoice %s: %s',
                    invoice['id'],
                    record_result.reason,
                )

            if subscription_id:
                djstripe_subscription = (
                    DjstripeSubscription.objects.filter(
                        id=subscription_id
                    ).first()
                )

                if djstripe_subscription:
                    local_subscription = (
                        Subscription.objects.filter(
                            djstripe_subscription=djstripe_subscription,
                            status='past_due'
                        ).first()
                    )

                    if local_subscription:
                        before_data = SubscriptionSerializer(
                            local_subscription
                        ).data
                        local_subscription.status = 'active'
                        local_subscription.save(update_fields=['status'])
                        SubscriptionService.handle_payment_success(
                            customer_id
                        )

                        logger.info(
                            f"Recovered subscription "
                            f"{local_subscription.id} "
                            f"from past_due to active"
                        )

                        def _send_success_notification(
                            *,
                            user_id=local_subscription.user_id,
                            amount=amount_paid,
                        ) -> None:
                            send_payment_success_notification.delay(
                                user_id=user_id,
                                amount=amount,
                            )

                        transaction.on_commit(
                            _send_success_notification
                        )
                        queue_billing_audit_event(
                            action_type='webhook.invoice.payment_succeeded',
                            source='webhook',
                            target_user_id=local_subscription.user_id,
                            target_username=local_subscription.user.username,
                            resource_type='subscription',
                            resource_id=local_subscription.id,
                            before_data=before_data,
                            after_data=SubscriptionSerializer(
                                local_subscription
                            ).data,
                            context={
                                'invoice_id': invoice['id'],
                                'customer_id': customer_id,
                                'amount_paid': amount_paid,
                            },
                        )

    except Exception as e:
        logger.error(
            f"Failed to process payment: {e}",
            exc_info=True
        )
        raise


@djstripe_receiver("invoice.payment_failed")
def handle_payment_failed(sender, **kwargs):
    """
    Handle payment failure synchronously

    Updates subscription status to 'past_due' and triggers
    user notification email.
    """
    event: Event = kwargs.get("event")
    invoice = event.data["object"]

    try:
        with transaction.atomic():
            customer_id = invoice["customer"]
            subscription_id = invoice.get("subscription")
            attempt_count = invoice.get("attempt_count", 1)
            last_error = invoice.get("last_payment_error", {})
            failure_reason = last_error.get("message", "Unknown error")

            logger.warning(
                f"Payment failed for customer {customer_id}, "
                f"subscription {subscription_id}, "
                f"attempt {attempt_count}, reason: {failure_reason}"
            )

            record_result = upsert_payment_record_from_stripe_invoice(
                invoice,
                source='webhook',
                event_type='invoice.payment_failed',
                status='failed',
            )
            if record_result.skipped:
                logger.warning(
                    'Skipped failed payment record sync for invoice %s: %s',
                    invoice['id'],
                    record_result.reason,
                )

            if subscription_id:
                djstripe_subscription = (
                    DjstripeSubscription.objects.filter(
                        id=subscription_id
                    ).first()
                )

                if djstripe_subscription:
                    local_subscription = (
                        Subscription.objects.filter(
                            djstripe_subscription=djstripe_subscription,
                            status='active'
                        ).first()
                    )

                    if local_subscription:
                        before_data = SubscriptionSerializer(
                            local_subscription
                        ).data
                        local_subscription.status = 'past_due'
                        local_subscription.save()

                        queue_billing_audit_event(
                            action_type='webhook.invoice.payment_failed',
                            source='webhook',
                            target_user_id=local_subscription.user_id,
                            target_username=local_subscription.user.username,
                            resource_type='subscription',
                            resource_id=local_subscription.id,
                            before_data=before_data,
                            after_data=SubscriptionSerializer(
                                local_subscription
                            ).data,
                            context={
                                'invoice_id': invoice['id'],
                                'customer_id': customer_id,
                                'attempt_count': attempt_count,
                                'failure_reason': failure_reason,
                            },
                        )

                        logger.info(
                            f"Updated subscription "
                            f"{local_subscription.id} to past_due status"
                        )

                        send_payment_failure_notification.delay(
                            user_id=local_subscription.user_id,
                            attempt_count=attempt_count,
                            failure_reason=failure_reason
                        )

                        logger.info(
                            f"Scheduled payment failure notification "
                            f"for user {local_subscription.user_id}"
                        )

    except Exception as e:
        logger.error(
            f"Failed to process payment_failed: {e}",
            exc_info=True
        )
        raise
