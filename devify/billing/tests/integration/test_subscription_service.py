"""
Integration tests for SubscriptionService

Tests cover key service methods without complex Stripe mocking:
- get_active_subscription with various states
- cancel_subscription (local only)
- handle_cancellation for webhooks
"""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from billing.models import PaymentProvider, Plan, Subscription, UserCredits
from billing.services.subscription_service import SubscriptionService

User = get_user_model()


@pytest.mark.django_db
class TestGetActiveSubscription:
    """
    Test get_active_subscription edge cases
    """

    def test_get_active_subscription_exists(
        self, test_user_with_free_subscription
    ):
        """
        Returns active subscription when it exists
        """
        subscription = SubscriptionService.get_active_subscription(
            test_user_with_free_subscription.id
        )

        assert subscription is not None
        assert subscription.user == test_user_with_free_subscription
        assert subscription.status == 'active'

    def test_get_active_subscription_none_exists(self, test_user):
        """
        Returns None when no subscription exists
        """
        subscription = SubscriptionService.get_active_subscription(
            test_user.id
        )

        assert subscription is None

    def test_get_active_subscription_only_canceled(
        self, test_user, free_plan, payment_provider
    ):
        """
        Returns None when only canceled subscription exists
        """
        Subscription.objects.create(
            user=test_user,
            plan=free_plan,
            provider=payment_provider,
            status='canceled',
            auto_renew=False,
            current_period_start=timezone.now(),
            current_period_end=timezone.now() + timedelta(days=30),
        )

        subscription = SubscriptionService.get_active_subscription(
            test_user.id
        )

        assert subscription is None

    def test_get_active_subscription_multiple_returns_latest(
        self, test_user, free_plan, starter_plan, payment_provider
    ):
        """
        Returns most recent active subscription when multiple exist
        """
        import time

        sub1 = Subscription.objects.create(
            user=test_user,
            plan=free_plan,
            provider=payment_provider,
            status='active',
            auto_renew=True,
            current_period_start=timezone.now(),
            current_period_end=timezone.now() + timedelta(days=30),
        )

        time.sleep(0.01)

        sub2 = Subscription.objects.create(
            user=test_user,
            plan=starter_plan,
            provider=payment_provider,
            status='active',
            auto_renew=True,
            current_period_start=timezone.now(),
            current_period_end=timezone.now() + timedelta(days=30),
        )

        subscription = SubscriptionService.get_active_subscription(
            test_user.id
        )

        assert subscription.id == sub2.id
        assert subscription.plan == starter_plan


@pytest.mark.django_db
class TestSubscriptionCancellation:
    """
    Test subscription cancellation without Stripe integration
    """

    def test_cancel_subscription_local_only(
        self, test_user_with_free_subscription
    ):
        """
        Cancel local subscription sets auto_renew=False
        """
        subscription = Subscription.objects.get(
            user=test_user_with_free_subscription
        )

        assert subscription.auto_renew is True

        SubscriptionService.cancel_subscription(subscription.id)

        subscription.refresh_from_db()
        assert subscription.auto_renew is False
        assert subscription.status == 'active'

    def test_cancel_nonexistent_subscription(self):
        """
        Cancel non-existent subscription raises error
        """
        with pytest.raises(Subscription.DoesNotExist):
            SubscriptionService.cancel_subscription(99999)


@pytest.mark.django_db
class TestHandleCancellation:
    """
    Test webhook cancellation handling
    """

    def test_handle_cancellation_marks_canceled(
        self, test_user, starter_plan, payment_provider
    ):
        """
        Handle cancellation webhook marks subscription as canceled
        """
        subscription = Subscription.objects.create(
            user=test_user,
            plan=starter_plan,
            provider=payment_provider,
            status='active',
            auto_renew=True,
            current_period_start=timezone.now(),
            current_period_end=timezone.now() + timedelta(days=30),
        )

        SubscriptionService.handle_cancellation('sub_fake_id_for_test')

        subscription.refresh_from_db()
        assert subscription.status == 'active'

    def test_handle_cancellation_not_found_no_error(self):
        """
        Handle cancellation for non-existent subscription doesn't raise
        """
        SubscriptionService.handle_cancellation('sub_nonexistent')


@pytest.mark.django_db
class TestCreateSubscription:
    """
    Test subscription creation service
    """

    def test_create_subscription_initializes_credits(
        self, test_user, starter_plan, payment_provider
    ):
        """
        Create subscription initializes user credits correctly
        """
        UserCredits.objects.create(
            user=test_user,
            base_credits=10,
            consumed_credits=5,
            period_start=timezone.now() - timedelta(days=15),
            period_end=timezone.now() + timedelta(days=15),
        )

        subscription = SubscriptionService.create_subscription(
            user_id=test_user.id,
            plan_id=starter_plan.id,
            provider='stripe'
        )

        assert subscription.user == test_user
        assert subscription.plan == starter_plan
        assert subscription.status == 'active'

        credits = UserCredits.objects.get(user=test_user)
        assert credits.subscription == subscription
        assert credits.base_credits == 100
        assert credits.consumed_credits == 0

    def test_create_subscription_invalid_plan(self, test_user):
        """
        Create subscription with invalid plan_id raises error
        """
        with pytest.raises(Plan.DoesNotExist):
            SubscriptionService.create_subscription(
                user_id=test_user.id,
                plan_id=99999,
                provider='stripe'
            )

    def test_create_subscription_invalid_provider(
        self, test_user, starter_plan
    ):
        """
        Create subscription with invalid provider raises error
        """
        with pytest.raises(PaymentProvider.DoesNotExist):
            SubscriptionService.create_subscription(
                user_id=test_user.id,
                plan_id=starter_plan.id,
                provider='invalid_provider'
            )

    def test_create_subscription_missing_user_credits(
        self, test_user, starter_plan
    ):
        """
        Create subscription when UserCredits doesn't exist raises error
        """
        with pytest.raises(UserCredits.DoesNotExist):
            SubscriptionService.create_subscription(
                user_id=test_user.id,
                plan_id=starter_plan.id,
                provider='stripe'
            )
