import logging
from datetime import datetime, timedelta

import stripe
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from djstripe.models import Customer, Subscription as DjstripeSubscription

from billing.models import (
    PaymentProvider,
    Plan,
    PlanPrice,
    Subscription,
    UserCredits,
)
from billing.constants import (
    PAYMENT_PROVIDER_NAMES,
    get_payment_provider_display_name,
    normalize_payment_provider_name,
)
from billing.services.djstripe_service import ensure_djstripe_owner_account
from billing.services.config_service import get_stripe_secret_key
from billing.services.customer_identity import resolve_customer_for_user
from billing.services.credits_service import CreditsService
from billing.services.stripe_compat import StripePlanMappingError, stripe_value

logger = logging.getLogger(__name__)

SUPPORTED_PAYMENT_PROVIDER_NAMES = set(PAYMENT_PROVIDER_NAMES.values())


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

    _stripe_value = staticmethod(stripe_value)

    @staticmethod
    def get_or_create_payment_provider(provider_name: str):
        provider_name = normalize_payment_provider_name(provider_name)
        if provider_name not in SUPPORTED_PAYMENT_PROVIDER_NAMES:
            raise PaymentProvider.DoesNotExist(
                f'Unsupported payment provider: {provider_name}'
            )
        payment_provider, _ = PaymentProvider.objects.get_or_create(
            name=provider_name,
            defaults={
                'display_name': get_payment_provider_display_name(
                    provider_name
                ),
                'is_active': True,
            },
        )
        return payment_provider

    @staticmethod
    @transaction.atomic
    def assign_free_plan_to_user(user):
        """
        Assign Free plan to a user

        Creates a Free plan subscription with initial credits.
        This is typically called during user registration as part of the
        default credits bootstrap flow.

        Args:
            user: Django User instance

        Returns:
            Subscription object

        Raises:
            BillingPlan.DoesNotExist: If Free plan not found
            PaymentProvider.DoesNotExist: If platform provider not found
        """
        free_plan = Plan.objects.get(slug='free')
        return SubscriptionService.switch_plan_for_user(user, free_plan)

    @staticmethod
    @transaction.atomic
    def switch_plan_for_user(
        user,
        plan: Plan,
        provider_name: str = 'platform',
    ):
        """
        Assign or switch a user to a specific plan.

        If the user already has an active subscription on the target plan,
        the subscription is kept and the credits are normalized to the plan.
        If the user has a different active subscription, the old one is
        canceled and a new one is created.
        """
        payment_provider = SubscriptionService.get_or_create_payment_provider(
            provider_name
        )

        current_time = timezone.now()
        period_days = plan.metadata.get('period_days', 30)
        period_end = current_time + timedelta(days=period_days)
        base_credits = plan.metadata.get('credits_per_period', 10)

        active_subscriptions = list(
            Subscription.objects.select_for_update().filter(
                user=user,
                status__in=['active', 'past_due', 'trialing'],
            ).select_related('plan', 'provider').order_by('-created_at')
        )
        existing_subscription = (
            active_subscriptions[0] if active_subscriptions else None
        )
        for duplicate_subscription in active_subscriptions[1:]:
            duplicate_subscription.status = 'canceled'
            duplicate_subscription.auto_renew = False
            duplicate_subscription.save(update_fields=['status', 'auto_renew'])

        can_reuse_subscription = (
            existing_subscription is not None
            and existing_subscription.plan_id == plan.id
            and existing_subscription.provider_id == payment_provider.id
            and existing_subscription.status == 'active'
        )
        if can_reuse_subscription:
            target_subscription = existing_subscription
        else:
            if existing_subscription:
                existing_subscription.status = 'canceled'
                existing_subscription.auto_renew = False
                existing_subscription.save(
                    update_fields=['status', 'auto_renew']
                )

            target_subscription = Subscription.objects.create(
                user=user,
                plan=plan,
                provider=payment_provider,
                status='active',
                current_period_start=current_time,
                current_period_end=period_end,
                auto_renew=True,
            )

        user_credits = CreditsService.get_user_credits(user.id)
        user_credits.subscription = target_subscription
        user_credits.base_credits = base_credits
        user_credits.consumed_credits = 0
        user_credits.period_start = (
            target_subscription.current_period_start
            if target_subscription
            else current_time
        )
        user_credits.period_end = (
            target_subscription.current_period_end
            if target_subscription
            else period_end
        )
        user_credits.save()

        logger.info(
            f"Assigned plan {plan.slug} to user {user.id}: "
            f"{base_credits} credits, {period_days} days period"
        )

        return target_subscription

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
        payment_provider = SubscriptionService.get_or_create_payment_provider(
            provider
        )

        active_subscriptions = list(
            Subscription.objects.select_for_update().filter(
                user=user,
                status__in=['active', 'past_due', 'trialing'],
            ).select_related('plan')
        )
        if active_subscriptions:
            logger.info(
                f"Canceling {len(active_subscriptions)} existing "
                f"subscriptions for user {user_id} before creating a new one"
            )
        for existing_subscription in active_subscriptions:
            existing_subscription.status = 'canceled'
            existing_subscription.auto_renew = False
            existing_subscription.save(update_fields=['status', 'auto_renew'])

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

        # Use CreditsService to handle duplicate records
        user_credits = CreditsService.get_user_credits(user_id)
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

        if not plan:
            raise StripePlanMappingError(price_id=price_id)

        # Get period dates from subscription items or billing cycle
        stripe.api_key = get_stripe_secret_key()
        stripe_sub = stripe.Subscription.retrieve(
            djstripe_subscription.id
        )

        # Try to get period from subscription items
        period_start = None
        period_end = None
        items = stripe_value(stripe_sub, 'items')
        item_data = stripe_value(items, 'data', []) or []
        if item_data:
            first_item = item_data[0]
            period_start = stripe_value(
                first_item,
                'current_period_start',
            )
            period_end = stripe_value(first_item, 'current_period_end')

        # Fallback to billing cycle anchor if not found
        if not period_start:
            period_start = stripe_value(stripe_sub, 'billing_cycle_anchor')

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

        # NOTE: Stripe cancellation state is expressed by cancel_at_period_end /
        # cancel_at. Do not infer auto_renew from status alone.
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
            # Use CreditsService to handle duplicate records
            user_credits = CreditsService.get_user_credits(user.id)
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
    def sync_from_stripe_subscription(stripe_subscription):
        """
        Sync a Stripe subscription object to the local database.

        NOTE: This is the shared entry point for both manual admin sync and
        Payment Check repairs. Keep all Stripe -> dj-stripe -> local conversion
        logic here so both paths stay identical.
        """
        stripe.api_key = get_stripe_secret_key()
        if not stripe.api_key:
            raise ValueError('Stripe secret key is not configured')

        ensure_djstripe_owner_account(stripe.api_key)
        djstripe_subscription = DjstripeSubscription.sync_from_stripe_data(
            stripe_subscription,
            api_key=stripe.api_key,
        )
        return SubscriptionService.sync_from_djstripe(djstripe_subscription)

    @staticmethod
    def _pick_recoverable_stripe_subscription(stripe_subscriptions):
        if not stripe_subscriptions:
            return None

        preferred_statuses = [
            'active',
            'trialing',
            'past_due',
            'incomplete',
            'unpaid',
        ]
        for status in preferred_statuses:
            candidates = [
                subscription
                for subscription in stripe_subscriptions
                if SubscriptionService._stripe_value(
                    subscription,
                    'status',
                ) == status
            ]
            if candidates:
                return max(
                    candidates,
                    key=lambda subscription: SubscriptionService._stripe_value(
                        subscription,
                        'created',
                        0,
                    ) or 0,
                )

        non_terminal = [
            subscription
            for subscription in stripe_subscriptions
            if SubscriptionService._stripe_value(
                subscription,
                'status',
            ) not in {'canceled', 'incomplete_expired'}
        ]
        if non_terminal:
            return max(
                non_terminal,
                key=lambda subscription: SubscriptionService._stripe_value(
                    subscription,
                    'created',
                    0,
                ) or 0,
            )
        return None

    @staticmethod
    @transaction.atomic
    def sync_user_subscription_from_stripe(user: User):
        """
        Recover local subscription state from the current Stripe state.

        This is intended for manual admin recovery when a webhook failed after
        a successful Stripe checkout/payment.
        """
        stripe.api_key = get_stripe_secret_key()
        if not stripe.api_key:
            raise ValueError('Stripe secret key is not configured')

        customer = resolve_customer_for_user(user)

        if not customer:
            raise ValueError('No Stripe customer found for this user')

        stripe_subscriptions = stripe.Subscription.list(
            customer=customer.id,
            status='all',
            limit=20,
        )
        stripe_subscription_items = list(getattr(stripe_subscriptions, 'data', []) or [])
        stripe_subscription = (
            SubscriptionService._pick_recoverable_stripe_subscription(
                stripe_subscription_items
            )
            or (
                max(
                    stripe_subscription_items,
                    key=lambda subscription: SubscriptionService._stripe_value(
                        subscription,
                        'created',
                        0,
                    )
                    or 0,
                )
                if stripe_subscription_items
                else None
            )
        )
        if not stripe_subscription:
            raise ValueError('No Stripe subscription found for this user')

        # NOTE: Reuse the shared Stripe sync entry point so manual sync and
        # Payment Check use the exact same conversion path.
        return SubscriptionService.sync_from_stripe_subscription(
            stripe_subscription
        )

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
            stripe.api_key = get_stripe_secret_key()

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
            stripe.api_key = get_stripe_secret_key()

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
                user_credits__djstripe_customer=customer,
                status='active'
            ).distinct()

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
                f"{customer_id}: {e}",
                exc_info=True,
            )
            raise
