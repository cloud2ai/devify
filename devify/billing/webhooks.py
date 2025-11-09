import logging

from django.contrib.auth.models import User
from django.db import transaction

from djstripe.event_handlers import djstripe_receiver
from djstripe.models import Event
from djstripe.models import Subscription as DjstripeSubscription

from billing.models import Subscription
from billing.services.credits_service import CreditsService
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
            if not customer.subscriber and customer.email:
                try:
                    user = User.objects.get(email=customer.email)
                    customer.subscriber = user
                    customer.save()
                    logger.info(
                        f"Auto-linked Customer {customer.id} to "
                        f"User {user.username}"
                    )
                except User.DoesNotExist:
                    logger.warning(
                        f"No User found for email {customer.email}, "
                        f"skipping subscription sync"
                    )
                    return

            SubscriptionService.sync_from_djstripe(
                djstripe_subscription
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
            if not customer.subscriber and customer.email:
                try:
                    user = User.objects.get(email=customer.email)
                    customer.subscriber = user
                    customer.save()
                    logger.info(
                        f"Auto-linked Customer {customer.id} to "
                        f"User {user.username}"
                    )
                except User.DoesNotExist:
                    logger.warning(
                        f"No User found for email {customer.email}"
                    )
                    return

            SubscriptionService.sync_from_djstripe(
                djstripe_subscription
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
        with transaction.atomic():
            SubscriptionService.handle_cancellation(
                subscription_id
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
        logger.info(
            f"Payment succeeded for customer {customer_id}, "
            f"invoice {invoice['id']}, subscription {subscription_id}, "
            f"amount: ${amount_paid:.2f}"
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
                    local_subscription.status = 'active'
                    local_subscription.save()

                    logger.info(
                        f"Recovered subscription "
                        f"{local_subscription.id} "
                        f"from past_due to active"
                    )

                    send_payment_success_notification.delay(
                        user_id=local_subscription.user_id,
                        amount=amount_paid
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
                        local_subscription.status = 'past_due'
                        local_subscription.save()

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
