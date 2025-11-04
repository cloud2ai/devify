import logging
from datetime import datetime, timedelta

import stripe
from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from djstripe.models import Customer

from billing.models import (
    PaymentProvider,
    Plan,
    PlanPrice,
    Subscription,
    UserCredits,
)
from billing.services.credits_service import CreditsService

logger = logging.getLogger(__name__)


class SubscriptionService:
    """
    Subscription management service
    """

    @staticmethod
    def get_active_subscription(user_id: int):
        """
        Get user's active subscription
        """
        return Subscription.objects.filter(
            user_id=user_id,
            status='active'
        ).order_by('-created_at').first()

    @staticmethod
    @transaction.atomic
    def create_subscription(
        user_id: int,
        plan_id: int,
        provider: str = 'stripe'
    ):
        """
        Create a new subscription
        """
        user = User.objects.get(id=user_id)
        plan = Plan.objects.get(id=plan_id)
        payment_provider = PaymentProvider.objects.get(name=provider)

        current_time = timezone.now()
        period_days = plan.metadata.get('period_days', 30)
        period_end = current_time + timedelta(days=period_days)

        subscription = Subscription.objects.create(
            user=user,
            plan=plan,
            provider=payment_provider,
            status='active',
            current_period_start=current_time,
            current_period_end=period_end,
            auto_renew=True
        )

        CreditsService.reset_period_credits(user_id)

        user_credits = UserCredits.objects.get(user_id=user_id)
        user_credits.subscription = subscription
        user_credits.save()

        logger.info(
            f"Created subscription for user {user_id}: "
            f"plan={plan.name}"
        )

        return subscription

    @staticmethod
    @transaction.atomic
    def sync_from_djstripe(djstripe_subscription):
        """
        Sync subscription from dj-stripe
        """
        customer = djstripe_subscription.customer
        user = customer.subscriber

        # Get plan info from subscription
        # djstripe_subscription.plan can be either Price object or dict
        plan_obj = djstripe_subscription.plan

        # Extract price ID
        if hasattr(plan_obj, 'id'):
            price_id = plan_obj.id
        elif isinstance(plan_obj, dict):
            price_id = plan_obj.get('id')
        else:
            price_id = None

        # Find local plan by price ID
        plan = None
        provider = None
        if price_id:
            plan_price = PlanPrice.objects.filter(
                provider_price_id=price_id
            ).first()
            if plan_price:
                plan = plan_price.plan
                provider = plan_price.provider

        # Fallback to free plan if no matching plan found
        if not plan:
            plan = Plan.objects.get(slug='free')
            provider = PaymentProvider.objects.filter(
                name='stripe'
            ).first()

        # Get period dates from subscription items or billing cycle
        stripe.api_key = settings.STRIPE_TEST_SECRET_KEY
        stripe_sub = stripe.Subscription.retrieve(
            djstripe_subscription.id
        )

        # Try to get period from subscription items
        period_start = None
        period_end = None
        if stripe_sub.get('items') and stripe_sub['items']['data']:
            first_item = stripe_sub['items']['data'][0]
            period_start = first_item.get('current_period_start')
            period_end = first_item.get('current_period_end')

        # Fallback to billing cycle anchor if not found
        if not period_start:
            period_start = stripe_sub.get('billing_cycle_anchor')

            # Calculate period end (30 days for monthly)
            if period_start:
                start_dt = datetime.fromtimestamp(period_start)
                period_end_dt = start_dt + timedelta(days=30)
                period_end = int(period_end_dt.timestamp())

        # Convert timestamps to datetime
        if period_start:
            period_start_dt = datetime.fromtimestamp(period_start)
            period_end_dt = datetime.fromtimestamp(period_end)
        else:
            # Last fallback: use current time
            period_start_dt = timezone.now()
            period_end_dt = period_start_dt + timedelta(days=30)

        subscription, created = Subscription.objects.update_or_create(
            djstripe_subscription=djstripe_subscription,
            defaults={
                'user': user,
                'plan': plan,
                'provider': provider,
                'status': djstripe_subscription.status,
                'current_period_start': period_start_dt,
                'current_period_end': period_end_dt,
                'auto_renew': (
                    not djstripe_subscription.cancel_at_period_end
                )
            }
        )

        if subscription.status == 'active':
            CreditsService.reset_period_credits(user.id)

            user_credits = UserCredits.objects.get(user_id=user.id)
            user_credits.subscription = subscription
            user_credits.djstripe_customer = customer
            user_credits.save()

        logger.info(
            f"Synced subscription from Stripe for user {user.id}"
        )

        return subscription

    @staticmethod
    @transaction.atomic
    def cancel_subscription(subscription_id: int):
        """
        Cancel subscription
        """
        subscription = Subscription.objects.get(id=subscription_id)

        if subscription.djstripe_subscription:
            subscription.djstripe_subscription.cancel()

        subscription.status = 'canceled'
        subscription.auto_renew = False
        subscription.save()

        logger.info(
            f"Canceled subscription {subscription_id} "
            f"for user {subscription.user_id}"
        )

    @staticmethod
    @transaction.atomic
    def handle_cancellation(subscription_id: str):
        """
        Handle subscription cancellation from Stripe
        """
        try:
            subscription = Subscription.objects.get(
                djstripe_subscription__id=subscription_id
            )
            subscription.status = 'canceled'
            subscription.auto_renew = False
            subscription.save()

            logger.info(
                f"Handled cancellation for "
                f"subscription {subscription_id}"
            )
        except Subscription.DoesNotExist:
            logger.warning(
                f"Subscription {subscription_id} not found "
                f"for cancellation"
            )

    @staticmethod
    @transaction.atomic
    def handle_payment_success(customer_id: str):
        """
        Handle successful payment from Stripe
        """
        try:
            customer = Customer.objects.get(id=customer_id)
            subscriptions = Subscription.objects.filter(
                djstripe_customer__id=customer_id,
                status='active'
            )

            for subscription in subscriptions:
                CreditsService.reset_period_credits(
                    subscription.user_id
                )

            logger.info(
                f"Handled payment success for "
                f"customer {customer_id}"
            )
        except Exception as e:
            logger.error(
                f"Error handling payment success for "
                f"{customer_id}: {e}"
            )
