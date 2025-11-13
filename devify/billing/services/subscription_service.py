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

    Handles all subscription-related operations including:
    - Creating and syncing subscriptions
    - Canceling and resuming subscriptions
    - Processing Stripe webhook events
    - Ensuring subscription uniqueness per user

    All payment operations are handled through Stripe API.
    """

    @staticmethod
    @transaction.atomic
    def assign_free_plan_to_user(user):
        """
        Assign Free plan to a user

        Creates a Free plan subscription with initial credits.
        This is typically called during user registration when
        BILLING_ENABLED=True.

        Args:
            user: Django User instance

        Returns:
            Subscription object

        Raises:
            BillingPlan.DoesNotExist: If Free plan not found
            PaymentProvider.DoesNotExist: If Stripe provider not found
        """
        # Check if user already has a subscription
        existing_subscription = Subscription.objects.filter(
            user=user
        ).first()
        if existing_subscription:
            logger.warning(
                f"User {user.id} already has subscription, "
                f"skipping Free plan assignment"
            )
            return existing_subscription

        # Get Free plan and payment provider
        free_plan = Plan.objects.get(slug='free')
        payment_provider = PaymentProvider.objects.get(name='stripe')

        current_time = timezone.now()
        period_days = free_plan.metadata.get('period_days', 30)
        period_end = current_time + timedelta(days=period_days)
        base_credits = free_plan.metadata.get('credits_per_period', 10)

        # Create Free plan subscription
        subscription = Subscription.objects.create(
            user=user,
            plan=free_plan,
            provider=payment_provider,
            status='active',
            current_period_start=current_time,
            current_period_end=period_end,
            auto_renew=True
        )

        # Initialize user credits
        UserCredits.objects.create(
            user=user,
            subscription=subscription,
            base_credits=base_credits,
            bonus_credits=0,
            consumed_credits=0,
            period_start=current_time,
            period_end=period_end,
            is_active=True
        )

        logger.info(
            f"Assigned Free plan to user {user.id}: "
            f"{base_credits} credits, {period_days} days period"
        )

        return subscription

    @staticmethod
    def get_active_subscription(user_id: int):
        """
        Get user's active subscription

        Returns the most recent active subscription for a user.
        Returns None if no active subscription exists.

        Args:
            user_id: User's database ID

        Returns:
            Subscription object or None
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
        Create a new subscription for a user

        Creates a local subscription record and initializes
        user credits based on the selected plan.

        Args:
            user_id: User's database ID
            plan_id: Plan's database ID
            provider: Payment provider name (default: 'stripe')

        Returns:
            Created Subscription object
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

        user_credits = UserCredits.objects.get(user_id=user_id)
        user_credits.subscription = subscription
        user_credits.save()

        CreditsService.reset_period_credits(user_id)

        logger.info(
            f"Created subscription for user {user_id}: "
            f"plan={plan.name}"
        )

        return subscription

    @staticmethod
    @transaction.atomic
    def sync_from_djstripe(djstripe_subscription):
        """
        Sync subscription from dj-stripe to local database

        Creates or updates local Subscription record based on
        Stripe subscription data. Ensures only one active
        subscription exists per user by canceling previous ones.

        Args:
            djstripe_subscription: djstripe Subscription model instance

        Returns:
            Synced Subscription object
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

        will_cancel = (
            djstripe_subscription.cancel_at_period_end or
            djstripe_subscription.cancel_at is not None
        )

        subscription, created = Subscription.objects.update_or_create(
            djstripe_subscription=djstripe_subscription,
            defaults={
                'user': user,
                'plan': plan,
                'provider': provider,
                'status': djstripe_subscription.status,
                'current_period_start': period_start_dt,
                'current_period_end': period_end_dt,
                'auto_renew': not will_cancel
            }
        )

        if created and subscription.status == 'active':
            old_active_subs = Subscription.objects.filter(
                user=user,
                status='active'
            ).exclude(id=subscription.id)

            if old_active_subs.exists():
                logger.info(
                    f"Canceling {old_active_subs.count()} old active "
                    f"subscriptions for user {user.id}"
                )
                old_active_subs.update(
                    status='canceled',
                    auto_renew=False
                )

        if subscription.status == 'active':
            user_credits = UserCredits.objects.get(user_id=user.id)
            user_credits.subscription = subscription
            user_credits.djstripe_customer = customer
            user_credits.save()

            CreditsService.reset_period_credits(user.id)

        logger.info(
            f"Synced subscription from Stripe for user {user.id}"
        )

        return subscription

    @staticmethod
    @transaction.atomic
    def cancel_subscription(subscription_id: int):
        """
        Cancel subscription at period end

        Sets cancel_at_period_end=True in Stripe and updates
        local auto_renew to False. Subscription remains active
        until the end of the current billing period.

        Args:
            subscription_id: Local subscription database ID

        Note:
            - Does NOT immediately delete the subscription
            - User can continue using until period_end
            - User can resume before period ends
        """
        subscription = Subscription.objects.get(id=subscription_id)

        if subscription.djstripe_subscription:
            stripe.api_key = (
                settings.STRIPE_LIVE_SECRET_KEY
                if settings.STRIPE_LIVE_MODE
                else settings.STRIPE_TEST_SECRET_KEY
            )

            stripe.Subscription.modify(
                subscription.djstripe_subscription.id,
                cancel_at_period_end=True
            )

        subscription.auto_renew = False
        subscription.save()

        logger.info(
            f"Scheduled cancellation for subscription "
            f"{subscription_id} for user {subscription.user_id} "
            f"at period end"
        )

    @staticmethod
    @transaction.atomic
    def resume_subscription(subscription_id: int):
        """
        Resume a cancelled subscription

        Sets cancel_at_period_end=False in Stripe to restore
        automatic renewal. User will be charged at the end of
        current period. No immediate payment required.

        Args:
            subscription_id: Local subscription database ID

        Note:
            - Only works for active subscriptions with auto_renew=False
            - No payment charged immediately
            - Next billing at current_period_end
        """
        subscription = Subscription.objects.get(id=subscription_id)

        if subscription.djstripe_subscription:
            stripe.api_key = (
                settings.STRIPE_LIVE_SECRET_KEY
                if settings.STRIPE_LIVE_MODE
                else settings.STRIPE_TEST_SECRET_KEY
            )

            stripe.Subscription.modify(
                subscription.djstripe_subscription.id,
                cancel_at_period_end=False
            )

        subscription.auto_renew = True
        subscription.save()

        logger.info(
            f"Resumed subscription {subscription_id} "
            f"for user {subscription.user_id}"
        )

    @staticmethod
    @transaction.atomic
    def handle_cancellation(subscription_id: str):
        """
        Handle subscription cancellation from Stripe webhook

        Called when customer.subscription.deleted webhook is
        received. Sets subscription status to canceled and
        disables auto-renewal.

        Args:
            subscription_id: Stripe subscription ID
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
        Handle successful payment from Stripe webhook

        Called when invoice.payment_succeeded webhook is received.
        Resets period credits for all active subscriptions of the
        customer.

        Args:
            customer_id: Stripe customer ID
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
