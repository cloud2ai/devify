from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from billing.services.customer_identity import (
    resolve_customer_for_user,
    resolve_user_for_customer,
    summarize_customer_identity_for_user,
)


@pytest.mark.django_db
def test_resolve_user_for_customer_uses_subscriber_only(test_user):
    customer = SimpleNamespace(
        subscriber=None,
        subscriber_id=None,
        email='wrong@example.com',
        metadata={'djstripe_subscriber': str(test_user.id)},
        save=Mock(),
    )

    user = resolve_user_for_customer(customer)

    assert user is None
    customer.save.assert_not_called()


@pytest.mark.django_db
def test_resolve_customer_for_user_uses_subscriber_only(
    test_user,
    mocker,
):
    customer = SimpleNamespace(
        subscriber=test_user,
        subscriber_id=test_user.id,
        metadata={'djstripe_subscriber': str(test_user.id)},
        save=Mock(),
    )

    class FakeQuerySet:
        def __init__(self, results):
            self._results = results

        def distinct(self):
            return self

        def __iter__(self):
            return iter(self._results)

    class FakeManager:
        def filter(self, *args, **kwargs):
            return FakeQuerySet([customer])

    select_related_mock = mocker.patch(
        'billing.services.customer_identity.Customer.objects.select_related',
        return_value=FakeManager(),
    )

    resolved = resolve_customer_for_user(test_user)

    assert resolved == customer
    customer.save.assert_not_called()
    select_related_mock.assert_called_once_with('subscriber')


@pytest.mark.django_db
def test_resolve_customer_for_user_returns_none_for_ambiguous_matches(
    test_user,
    mocker,
):
    customer_one = SimpleNamespace(
        id='cus_1',
        subscriber=test_user,
        subscriber_id=test_user.id,
        metadata={'djstripe_subscriber': str(test_user.id)},
        save=Mock(),
    )
    customer_two = SimpleNamespace(
        id='cus_2',
        subscriber=test_user,
        subscriber_id=test_user.id,
        metadata={'user_id': str(test_user.id)},
        save=Mock(),
    )

    class FakeQuerySet:
        def __init__(self, results):
            self._results = results

        def distinct(self):
            return self

        def __iter__(self):
            return iter(self._results)

    class FakeManager:
        def filter(self, *args, **kwargs):
            return FakeQuerySet([customer_one, customer_two])

    mocker.patch(
        'billing.services.customer_identity.Customer.objects.select_related',
        return_value=FakeManager(),
    )

    resolved = resolve_customer_for_user(test_user)

    assert resolved is None
    assert customer_one.save.call_count == 0
    assert customer_two.save.call_count == 0


@pytest.mark.django_db
def test_summarize_customer_identity_for_user_reports_conflicts(
    test_user,
    mocker,
):
    customer_one = SimpleNamespace(
        id='cus_1',
        subscriber=test_user,
        subscriber_id=test_user.id,
        metadata={'djstripe_subscriber': str(test_user.id)},
        email='one@example.com',
    )
    customer_two = SimpleNamespace(
        id='cus_2',
        subscriber=SimpleNamespace(username='admin'),
        subscriber_id=test_user.id,
        metadata={'user_id': str(test_user.id)},
        email='two@example.com',
    )

    class FakeQuerySet:
        def __init__(self, results):
            self._results = results

        def distinct(self):
            return self

        def __iter__(self):
            return iter(self._results)

    class FakeManager:
        def filter(self, *args, **kwargs):
            return FakeQuerySet([customer_one, customer_two])

    mocker.patch(
        'billing.services.customer_identity.Customer.objects.select_related',
        return_value=FakeManager(),
    )

    summary = summarize_customer_identity_for_user(test_user)

    assert summary['has_conflict'] is True
    assert summary['match_count'] == 2
    assert summary['customer_ids'] == ['cus_1', 'cus_2']
    assert summary['customers'][0]['match_sources'] == ['subscriber']
