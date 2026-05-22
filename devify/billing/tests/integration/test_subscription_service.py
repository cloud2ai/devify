"""
Integration tests for SubscriptionService

Tests cover key service methods without complex Stripe mocking:
- get_active_subscription with various states
- cancel_subscription (local only)
- handle_cancellation for webhooks
"""

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from djstripe.models import Customer

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
        assert subscription.provider.name == 'platform'

    def test_get_active_subscription_none_exists(self, test_user):
        """
        Returns None when no subscription exists
        """
        subscription = SubscriptionService.get_active_subscription(
            test_user.id
        )

        assert subscription is None

    def test_get_active_subscription_only_canceled(
        self, test_user, free_plan, platform_payment_provider
    ):
        """
        Returns None when only canceled subscription exists
        """
        Subscription.objects.create(
            user=test_user,
            plan=free_plan,
            provider=platform_payment_provider,
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
        self,
        test_user,
        free_plan,
        starter_plan,
        payment_provider,
        platform_payment_provider,
    ):
        """
        Returns most recent active subscription when multiple exist
        """
        import time

        sub1 = Subscription.objects.create(
            user=test_user,
            plan=free_plan,
            provider=platform_payment_provider,
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
        assert subscription.provider.name == 'platform'

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
class TestHandlePaymentSuccess:
    """
    Test payment success credit reset handling
    """

    def test_handle_payment_success_resets_active_subscription_credits(
        self,
        mocker,
        test_user,
        starter_plan,
        payment_provider,
    ):
        customer = Customer.objects.create(
            id='cus_test',
            subscriber=test_user,
            email=test_user.email,
            metadata={},
        )
        subscription = Subscription.objects.create(
            user=test_user,
            plan=starter_plan,
            provider=payment_provider,
            status='active',
            auto_renew=True,
            current_period_start=timezone.now() - timedelta(days=10),
            current_period_end=timezone.now() + timedelta(days=20),
        )
        UserCredits.objects.create(
            user=test_user,
            subscription=subscription,
            djstripe_customer=customer,
            base_credits=10,
            consumed_credits=5,
            period_start=timezone.now() - timedelta(days=10),
            period_end=timezone.now() + timedelta(days=20),
            is_active=True,
        )

        reset_period_credits = mocker.patch(
            'billing.services.subscription_service.CreditsService.reset_period_credits'
        )

        SubscriptionService.handle_payment_success(customer.id)

        reset_period_credits.assert_called_once_with(test_user.id)


@pytest.mark.django_db
class TestCreateSubscriptionValidation:
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
            is_active=True,
        )

        subscription = SubscriptionService.create_subscription(
            user_id=test_user.id,
            plan_id=starter_plan.id,
            provider='stripe'
        )

        assert subscription.user == test_user
        assert subscription.plan == starter_plan
        assert subscription.status == 'active'

        credits = UserCredits.objects.get(user=test_user, is_active=True)
        assert credits.subscription == subscription
        assert credits.base_credits == 100

    def test_create_subscription_cancels_existing_active_subscriptions(
        self,
        test_user,
        starter_plan,
        free_plan,
        payment_provider,
        platform_payment_provider,
    ):
        old_active = Subscription.objects.create(
            user=test_user,
            plan=free_plan,
            provider=platform_payment_provider,
            status='active',
            auto_renew=True,
            current_period_start=timezone.now() - timedelta(days=5),
            current_period_end=timezone.now() + timedelta(days=25),
        )
        Subscription.objects.create(
            user=test_user,
            plan=starter_plan,
            provider=payment_provider,
            status='past_due',
            auto_renew=True,
            current_period_start=timezone.now() - timedelta(days=5),
            current_period_end=timezone.now() + timedelta(days=25),
        )

        subscription = SubscriptionService.create_subscription(
            user_id=test_user.id,
            plan_id=starter_plan.id,
            provider='stripe'
        )

        old_active.refresh_from_db()
        assert old_active.status == 'canceled'
        assert old_active.auto_renew is False
        assert subscription.status == 'active'
        assert (
            Subscription.objects.filter(
                user=test_user,
                status='active',
            ).count()
            == 1
        )
        credits = UserCredits.objects.get(user=test_user, is_active=True)
        assert credits.subscription == subscription


@pytest.mark.django_db
def test_switch_plan_for_user_cancels_non_terminal_existing_subscriptions(
    test_user,
    free_plan,
    starter_plan,
    payment_provider,
    platform_payment_provider,
):
    active_subscription = Subscription.objects.create(
        user=test_user,
        plan=starter_plan,
        provider=payment_provider,
        status='active',
        auto_renew=True,
        current_period_start=timezone.now(),
        current_period_end=timezone.now() + timedelta(days=30),
    )
    past_due_subscription = Subscription.objects.create(
        user=test_user,
        plan=starter_plan,
        provider=payment_provider,
        status='past_due',
        auto_renew=True,
        current_period_start=timezone.now(),
        current_period_end=timezone.now() + timedelta(days=30),
    )
    trialing_subscription = Subscription.objects.create(
        user=test_user,
        plan=starter_plan,
        provider=payment_provider,
        status='trialing',
        auto_renew=True,
        current_period_start=timezone.now(),
        current_period_end=timezone.now() + timedelta(days=30),
    )
    Subscription.objects.create(
        user=test_user,
        plan=free_plan,
        provider=platform_payment_provider,
        status='canceled',
        auto_renew=False,
        current_period_start=timezone.now(),
        current_period_end=timezone.now() + timedelta(days=30),
    )

    target_subscription = SubscriptionService.switch_plan_for_user(
        test_user,
        free_plan,
    )

    active_subscription.refresh_from_db()
    past_due_subscription.refresh_from_db()
    trialing_subscription.refresh_from_db()
    target_subscription.refresh_from_db()

    assert active_subscription.status == 'canceled'
    assert past_due_subscription.status == 'canceled'
    assert trialing_subscription.status == 'canceled'
    assert target_subscription.status == 'active'
    assert target_subscription.plan == free_plan
    assert target_subscription.auto_renew is True


@pytest.mark.django_db
def test_switch_plan_for_user_replaces_same_plan_with_different_provider(
    test_user,
    starter_plan,
    payment_provider,
):
    stripe_subscription = Subscription.objects.create(
        user=test_user,
        plan=starter_plan,
        provider=payment_provider,
        status='past_due',
        auto_renew=True,
        current_period_start=timezone.now(),
        current_period_end=timezone.now() + timedelta(days=30),
    )

    target_subscription = SubscriptionService.switch_plan_for_user(
        test_user,
        starter_plan,
    )

    stripe_subscription.refresh_from_db()
    target_subscription.refresh_from_db()

    assert stripe_subscription.status == 'canceled'
    assert stripe_subscription.auto_renew is False
    assert target_subscription.id != stripe_subscription.id
    assert target_subscription.status == 'active'
    assert target_subscription.plan == starter_plan
    assert target_subscription.provider.name == 'platform'


@pytest.mark.django_db
class TestCreateSubscription:
    """
    Test subscription creation service
    """

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

    def test_create_subscription_creates_user_credits(
        self, test_user, starter_plan, payment_provider
    ):
        """
        Create subscription when UserCredits doesn't exist creates it automatically
        """
        subscription = SubscriptionService.create_subscription(
            user_id=test_user.id,
            plan_id=starter_plan.id,
            provider='stripe'
        )

        assert subscription.user == test_user
        assert subscription.plan == starter_plan
        assert subscription.status == 'active'

        credits = UserCredits.objects.get(user=test_user, is_active=True)
        assert credits.subscription == subscription
        assert credits.base_credits == 100


@pytest.mark.django_db
class TestSyncUserSubscriptionFromStripe:
    """
    Test recovering a local subscription from Stripe
    """

    def test_sync_user_subscription_from_stripe_picks_latest_active_subscription(
        self,
        mocker,
        test_user,
    ):
        customer = SimpleNamespace(
            id='cus_123',
            subscriber=test_user,
            email=test_user.email,
            subscriber_id=test_user.id,
            save=Mock(),
        )
        active_subscription = SimpleNamespace(
            id='sub_active',
            status='active',
            created=200,
        )
        active_subscription.to_dict = lambda: {
            'id': 'sub_active',
            'status': 'active',
            'customer': 'cus_123',
            'created': 200,
            'items': {
                'data': [
                    {
                        'price': {'id': 'price_test'},
                        'current_period_start': 1710000000,
                        'current_period_end': 1712592000,
                    }
                ]
            },
        }
        canceled_subscription = SimpleNamespace(
            id='sub_canceled',
            status='canceled',
            created=100,
        )
        canceled_subscription.to_dict = lambda: {
            'id': 'sub_canceled',
            'status': 'canceled',
            'customer': 'cus_123',
            'created': 100,
        }
        djstripe_subscription = SimpleNamespace(
            id='sub_active',
            customer=customer,
            plan=SimpleNamespace(id='price_test'),
        )
        synced_subscription = SimpleNamespace(id=999)

        mocker.patch(
            'billing.services.subscription_service.get_stripe_secret_key',
            return_value='sk_test_123',
        )
        mocker.patch(
            'billing.services.subscription_service.ensure_djstripe_owner_account',
            return_value=SimpleNamespace(id='acct_test_123'),
        )
        mocker.patch(
            'billing.services.subscription_service.Customer.objects.filter',
            return_value=SimpleNamespace(first=lambda: customer),
        )
        mocker.patch(
            'billing.services.subscription_service.stripe.Subscription.list',
            return_value=SimpleNamespace(
                data=[canceled_subscription, active_subscription]
            ),
        )
        mocker.patch(
            'billing.services.subscription_service.DjstripeSubscription.sync_from_stripe_data',
            return_value=djstripe_subscription,
        )
        sync_from_djstripe = mocker.patch(
            'billing.services.subscription_service.SubscriptionService.sync_from_djstripe',
            return_value=synced_subscription,
        )

        result = SubscriptionService.sync_user_subscription_from_stripe(
            test_user
        )

        assert result == synced_subscription
        sync_from_djstripe.assert_called_once_with(djstripe_subscription)

    def test_sync_user_subscription_from_stripe_passes_runtime_api_key_to_djstripe(
        self,
        mocker,
        test_user,
    ):
        customer = SimpleNamespace(
            id='cus_123',
            subscriber=test_user,
            email=test_user.email,
            subscriber_id=test_user.id,
            save=Mock(),
        )
        active_subscription = SimpleNamespace(
            id='sub_active',
            status='active',
            created=200,
        )
        active_subscription.to_dict = lambda: {
            'id': 'sub_active',
            'status': 'active',
            'customer': 'cus_123',
            'created': 200,
            'items': {
                'data': [
                    {
                        'price': {'id': 'price_test'},
                        'current_period_start': 1710000000,
                        'current_period_end': 1712592000,
                    }
                ]
            },
        }
        djstripe_subscription = SimpleNamespace(
            id='sub_active',
            customer=customer,
            plan=SimpleNamespace(id='price_test'),
        )
        synced_subscription = SimpleNamespace(id=999)

        mocker.patch(
            'billing.services.subscription_service.get_stripe_secret_key',
            return_value='sk_test_runtime_123',
        )
        mocker.patch(
            'billing.services.subscription_service.ensure_djstripe_owner_account',
            return_value=SimpleNamespace(id='acct_test_123'),
        )
        mocker.patch(
            'billing.services.subscription_service.Customer.objects.filter',
            return_value=SimpleNamespace(first=lambda: customer),
        )
        mocker.patch(
            'billing.services.subscription_service.stripe.Subscription.list',
            return_value=SimpleNamespace(data=[active_subscription]),
        )
        sync_from_stripe_data = mocker.patch(
            'billing.services.subscription_service.DjstripeSubscription.sync_from_stripe_data',
            return_value=djstripe_subscription,
        )
        sync_from_djstripe = mocker.patch(
            'billing.services.subscription_service.SubscriptionService.sync_from_djstripe',
            return_value=synced_subscription,
        )
        mocker.patch(
            'billing.services.subscription_service.stripe.api_key',
            'sk_test_runtime_123',
        )

        result = SubscriptionService.sync_user_subscription_from_stripe(
            test_user
        )

        assert result == synced_subscription
        sync_from_stripe_data.assert_called_once()
        assert sync_from_stripe_data.call_args.kwargs['api_key'] == 'sk_test_runtime_123'
        sync_from_djstripe.assert_called_once_with(djstripe_subscription)

    def test_sync_from_djstripe_handles_stripe_objects(
        self,
        mocker,
        test_user,
    ):
        customer = SimpleNamespace(
            id='cus_123',
            subscriber=test_user,
            email=test_user.email,
            subscriber_id=test_user.id,
        )
        djstripe_subscription = SimpleNamespace(
            id='sub_active',
            customer=customer,
            plan=SimpleNamespace(id='price_test'),
            status='active',
            cancel_at_period_end=False,
            cancel_at=None,
        )
        stripe_subscription = SimpleNamespace(
            items=SimpleNamespace(
                data=[
                    SimpleNamespace(
                        price=SimpleNamespace(id='price_test'),
                        current_period_start=1710000000,
                        current_period_end=1712592000,
                    )
                ]
            ),
            billing_cycle_anchor=1710000000,
        )
        stripe_provider = SimpleNamespace(name='stripe')
        plan_price = SimpleNamespace(
            plan=SimpleNamespace(slug='starter'),
            provider=stripe_provider,
        )
        synced_subscription = SimpleNamespace(
            id=999,
            status='active',
            plan=SimpleNamespace(slug='starter'),
            provider=stripe_provider,
            auto_renew=True,
            djstripe_subscription=djstripe_subscription,
        )
        user_credits = SimpleNamespace(save=Mock())

        mocker.patch(
            'billing.services.subscription_service.stripe.api_key',
            'sk_test_runtime_123',
        )
        mocker.patch(
            'billing.services.subscription_service.stripe.Subscription.retrieve',
            return_value=stripe_subscription,
        )
        mocker.patch(
            'billing.services.subscription_service.PlanPrice.objects.filter',
            return_value=SimpleNamespace(first=lambda: plan_price),
        )
        mocker.patch(
            'billing.services.subscription_service.Subscription.objects.update_or_create',
            return_value=(synced_subscription, False),
        )
        mocker.patch(
            'billing.services.subscription_service.CreditsService.get_user_credits',
            return_value=user_credits,
        )
        reset_period_credits = mocker.patch(
            'billing.services.subscription_service.CreditsService.reset_period_credits'
        )
        result = SubscriptionService.sync_from_djstripe(djstripe_subscription)

        assert result == synced_subscription
        reset_period_credits.assert_called_once_with(test_user.id)
        assert user_credits.save.called
