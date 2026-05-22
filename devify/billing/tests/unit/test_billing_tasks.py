from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


class _FakeQuerySet:
    def __init__(self, results):
        self._results = results

    def select_related(self, *args, **kwargs):
        return self

    def count(self):
        return len(self._results)

    def __iter__(self):
        return iter(self._results)


@pytest.mark.django_db
def test_downgrade_task_calls_stripe_cancel_for_linked_subscription(mocker):
    from billing.tasks import downgrade_failed_paid_subscriptions

    fake_user = SimpleNamespace(id=1, username='alice')
    fake_plan = SimpleNamespace(name='Starter', slug='starter', metadata={})
    fake_subscription = SimpleNamespace(
        id=10,
        user=fake_user,
        plan=fake_plan,
        status='past_due',
        auto_renew=True,
        djstripe_subscription=SimpleNamespace(id='sub_123'),
        save=Mock(),
        refresh_from_db=Mock(),
    )
    fake_free_plan = SimpleNamespace(slug='free', metadata={})
    fake_provider = SimpleNamespace(name='platform')
    fake_credits = SimpleNamespace(
        base_credits=10,
        bonus_credits=0,
        consumed_credits=5,
        period_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
        period_end=datetime(2024, 1, 31, tzinfo=timezone.utc),
        save=Mock(),
    )
    fake_new_subscription = SimpleNamespace(
        id=20,
        user=fake_user,
        plan=fake_free_plan,
        provider=fake_provider,
        status='active',
        auto_renew=False,
        current_period_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
        current_period_end=datetime(2024, 1, 31, tzinfo=timezone.utc),
    )

    mocker.patch(
        'billing.tasks.Subscription.objects.filter',
        return_value=_FakeQuerySet([fake_subscription]),
    )
    mocker.patch(
        'billing.tasks.Subscription.objects.create',
        return_value=fake_new_subscription,
    )
    mocker.patch(
        'billing.models.Plan.objects.get',
        return_value=fake_free_plan,
    )
    mocker.patch(
        'billing.services.subscription_service.SubscriptionService.get_or_create_payment_provider',
        return_value=fake_provider,
    )
    cancel_mock = mocker.patch(
        'billing.services.subscription_service.SubscriptionService.cancel_subscription'
    )
    mocker.patch(
        'billing.tasks.CreditsService.get_user_credits',
        return_value=fake_credits,
    )
    mocker.patch(
        'billing.tasks.SubscriptionSerializer',
        side_effect=lambda obj: SimpleNamespace(data={'id': obj.id}),
    )
    mocker.patch('billing.tasks.queue_billing_audit_event')

    class FakeTracer:
        def create_task(self, *args, **kwargs):
            return None

        def append_task(self, *args, **kwargs):
            return None

        def complete_task(self, *args, **kwargs):
            return None

        def fail_task(self, *args, **kwargs):
            return None

    mocker.patch('billing.tasks.TaskTracer', return_value=FakeTracer())
    mocker.patch(
        'billing.tasks.timezone.now',
        return_value=datetime(2024, 2, 1, tzinfo=timezone.utc),
    )

    result = downgrade_failed_paid_subscriptions()

    assert result['downgraded'] == 1
    cancel_mock.assert_called_once_with(fake_subscription.id)
    fake_subscription.refresh_from_db.assert_called_once()
    fake_subscription.save.assert_called_once_with(
        update_fields=['status', 'auto_renew']
    )
    assert fake_subscription.status == 'canceled'
    assert fake_subscription.auto_renew is False
