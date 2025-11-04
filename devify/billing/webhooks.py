import logging

from django.contrib.auth.models import User
from django.db import transaction
from djstripe.event_handlers import djstripe_receiver
from djstripe.models import Event, Subscription as DjstripeSubscription

from billing.services.credits_service import CreditsService
from billing.services.subscription_service import SubscriptionService

logger = logging.getLogger(__name__)


@djstripe_receiver("customer.subscription.created")
def handle_subscription_created(sender, **kwargs):
    """
    Synchronous webhook handling with robust error handling
    """
    event: Event = kwargs.get("event")
    subscription_id = event.data["object"]["id"]

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

    Note: Credit allocation is handled by subscription webhooks.
    This handler mainly logs successful payments for monitoring.
    If subscription is renewed, the subscription.updated webhook
    will handle credit reset automatically.
    """
    event: Event = kwargs.get("event")
    invoice = event.data["object"]
    customer_id = invoice["customer"]
    subscription_id = invoice.get("subscription")

    try:
        logger.info(
            f"Payment succeeded for customer {customer_id}, "
            f"invoice {invoice['id']}, "
            f"subscription {subscription_id}"
        )

        # Subscription renewal credits reset is handled by
        # subscription.updated webhook automatically

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
    """
    event: Event = kwargs.get("event")
    invoice = event.data["object"]

    try:
        with transaction.atomic():
            customer_id = invoice["customer"]
            logger.warning(
                f"Payment failed for customer: {customer_id}"
            )

    except Exception as e:
        logger.error(
            f"Failed to process payment_failed: {e}",
            exc_info=True
        )
        raise
