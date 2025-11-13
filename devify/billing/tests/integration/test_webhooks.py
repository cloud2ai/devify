"""
Integration tests for Stripe webhook handlers

Tests webhook event processing:
- customer.subscription.created
- customer.subscription.updated
- customer.subscription.deleted
- invoice.payment_succeeded
- invoice.payment_failed
"""

from datetime import timedelta
from unittest.mock import Mock, patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from billing.models import Subscription
from billing.webhooks import (
    handle_payment_failed,
    handle_payment_succeeded,
    handle_subscription_created,
    handle_subscription_deleted,
    handle_subscription_updated,
)

User = get_user_model()


@pytest.mark.django_db
class TestSubscriptionCreatedWebhook:
    """
    Test customer.subscription.created webhook
    """

    @patch('billing.webhooks.SubscriptionService.sync_from_djstripe')
    def test_subscription_created_syncs_to_local(
        self, mock_sync, test_user
    ):
        """
        subscription.created webhook syncs djstripe to local
        """
        djstripe_sub = Mock()
        djstripe_sub.id = 'sub_created_123'
        djstripe_sub.customer = Mock()
        djstripe_sub.customer.subscriber = test_user
        djstripe_sub.customer.email = test_user.email

        event = Mock()
        event.data = {
            'object': {
                'id': 'sub_created_123'
            }
        }

        with patch(
            'billing.webhooks.DjstripeSubscription.objects.get',
            return_value=djstripe_sub
        ):
            handle_subscription_created(None, event=event)

        mock_sync.assert_called_once_with(djstripe_sub)

    @patch('billing.webhooks.SubscriptionService.sync_from_djstripe')
    def test_subscription_created_auto_links_customer(
        self, mock_sync, test_user
    ):
        """
        Auto-link Customer to User if subscriber is None
        """
        djstripe_sub = Mock()
        djstripe_sub.id = 'sub_link_123'
        djstripe_sub.customer = Mock()
        djstripe_sub.customer.subscriber = None
        djstripe_sub.customer.email = test_user.email
        djstripe_sub.customer.save = Mock()

        event = Mock()
        event.data = {
            'object': {
                'id': 'sub_link_123'
            }
        }

        with patch(
            'billing.webhooks.DjstripeSubscription.objects.get',
            return_value=djstripe_sub
        ):
            handle_subscription_created(None, event=event)

        assert djstripe_sub.customer.subscriber == test_user
        djstripe_sub.customer.save.assert_called_once()
        mock_sync.assert_called_once()


@pytest.mark.django_db
class TestSubscriptionUpdatedWebhook:
    """
    Test customer.subscription.updated webhook
    """

    @patch('billing.webhooks.SubscriptionService.sync_from_djstripe')
    def test_subscription_updated_syncs_to_local(
        self, mock_sync, test_user
    ):
        """
        subscription.updated webhook syncs changes to local
        """
        djstripe_sub = Mock()
        djstripe_sub.id = 'sub_updated_123'
        djstripe_sub.customer = Mock()
        djstripe_sub.customer.subscriber = test_user
        djstripe_sub.customer.email = test_user.email

        event = Mock()
        event.data = {
            'object': {
                'id': 'sub_updated_123'
            }
        }

        with patch(
            'billing.webhooks.DjstripeSubscription.objects.get',
            return_value=djstripe_sub
        ):
            handle_subscription_updated(None, event=event)

        mock_sync.assert_called_once_with(djstripe_sub)


@pytest.mark.django_db
class TestSubscriptionDeletedWebhook:
    """
    Test customer.subscription.deleted webhook
    """

    @patch('billing.webhooks.SubscriptionService.handle_cancellation')
    def test_subscription_deleted_calls_cancellation(
        self, mock_handle_cancellation
    ):
        """
        subscription.deleted webhook calls handle_cancellation
        """
        event = Mock()
        event.data = {
            'object': {
                'id': 'sub_deleted_123'
            }
        }

        handle_subscription_deleted(None, event=event)

        mock_handle_cancellation.assert_called_once_with('sub_deleted_123')


@pytest.mark.django_db
class TestPaymentSucceededWebhook:
    """
    Test invoice.payment_succeeded webhook
    """

    @patch('billing.webhooks.send_payment_success_notification.delay')
    @patch('billing.webhooks.Subscription.objects.filter')
    @patch('billing.webhooks.DjstripeSubscription.objects.filter')
    def test_payment_succeeded_recovers_past_due_subscription(
        self, mock_djstripe_filter, mock_subscription_filter,
        mock_send_email, test_user, starter_plan, payment_provider
    ):
        """
        Payment success recovers past_due subscription to active
        """
        subscription = Subscription.objects.create(
            user=test_user,
            plan=starter_plan,
            provider=payment_provider,
            status='past_due',
            auto_renew=True,
            current_period_start=timezone.now(),
            current_period_end=timezone.now() + timedelta(days=30),
        )

        djstripe_sub = Mock()
        djstripe_sub.id = 'sub_payment_success'

        event = Mock()
        event.data = {
            'object': {
                'id': 'inv_123',
                'customer': 'cus_123',
                'subscription': 'sub_payment_success',
                'amount_paid': 2999
            }
        }

        mock_djstripe_filter.return_value.first.return_value = djstripe_sub
        mock_subscription_filter.return_value.first.return_value = subscription

        handle_payment_succeeded(None, event=event)

        subscription.refresh_from_db()
        assert subscription.status == 'active'

        mock_send_email.assert_called_once_with(
            user_id=test_user.id,
            amount=29.99
        )

    @patch('billing.webhooks.send_payment_success_notification.delay')
    @patch('billing.webhooks.Subscription.objects.filter')
    @patch('billing.webhooks.DjstripeSubscription.objects.filter')
    def test_payment_succeeded_active_subscription_no_change(
        self, mock_djstripe_filter, mock_subscription_filter,
        mock_send_email, test_user, starter_plan, payment_provider
    ):
        """
        Payment success for active subscription does not send email
        """
        djstripe_sub = Mock()
        djstripe_sub.id = 'sub_already_active'

        event = Mock()
        event.data = {
            'object': {
                'id': 'inv_456',
                'customer': 'cus_456',
                'subscription': 'sub_already_active',
                'amount_paid': 2999
            }
        }

        mock_djstripe_filter.return_value.first.return_value = djstripe_sub
        mock_subscription_filter.return_value.first.return_value = None

        handle_payment_succeeded(None, event=event)

        mock_send_email.assert_not_called()


@pytest.mark.django_db
class TestPaymentFailedWebhook:
    """
    Test invoice.payment_failed webhook
    """

    @patch('billing.webhooks.send_payment_failure_notification.delay')
    @patch('billing.webhooks.Subscription.objects.filter')
    @patch('billing.webhooks.DjstripeSubscription.objects.filter')
    def test_payment_failed_sets_past_due_status(
        self, mock_djstripe_filter, mock_subscription_filter,
        mock_send_email, test_user, starter_plan, payment_provider
    ):
        """
        Payment failure sets subscription to past_due
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

        djstripe_sub = Mock()
        djstripe_sub.id = 'sub_payment_failed'

        event = Mock()
        event.data = {
            'object': {
                'id': 'inv_fail_123',
                'customer': 'cus_fail_123',
                'subscription': 'sub_payment_failed',
                'attempt_count': 2,
                'last_payment_error': {
                    'message': 'Card declined'
                }
            }
        }

        mock_djstripe_filter.return_value.first.return_value = djstripe_sub
        mock_subscription_filter.return_value.first.return_value = subscription

        handle_payment_failed(None, event=event)

        subscription.refresh_from_db()
        assert subscription.status == 'past_due'

        mock_send_email.assert_called_once_with(
            user_id=test_user.id,
            attempt_count=2,
            failure_reason='Card declined'
        )

    @patch('billing.webhooks.send_payment_failure_notification.delay')
    @patch('billing.webhooks.Subscription.objects.filter')
    @patch('billing.webhooks.DjstripeSubscription.objects.filter')
    def test_payment_failed_past_due_subscription_no_duplicate_email(
        self, mock_djstripe_filter, mock_subscription_filter,
        mock_send_email, test_user, starter_plan, payment_provider
    ):
        """
        Payment failure for already past_due subscription
        """
        djstripe_sub = Mock()
        djstripe_sub.id = 'sub_already_past_due'

        event = Mock()
        event.data = {
            'object': {
                'id': 'inv_fail_456',
                'customer': 'cus_fail_456',
                'subscription': 'sub_already_past_due',
                'attempt_count': 3,
                'last_payment_error': {
                    'message': 'Insufficient funds'
                }
            }
        }

        mock_djstripe_filter.return_value.first.return_value = djstripe_sub
        mock_subscription_filter.return_value.first.return_value = None

        handle_payment_failed(None, event=event)

        mock_send_email.assert_not_called()
