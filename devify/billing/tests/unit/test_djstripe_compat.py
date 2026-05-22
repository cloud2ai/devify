import stripe
from unittest.mock import Mock

import pytest
from types import SimpleNamespace

from djstripe.models import Account, APIKey

from billing.services.djstripe_service import ensure_djstripe_owner_account
from billing.services.stripe_compat import StripePlanMappingError
from billing.services.subscription_service import SubscriptionService


@pytest.mark.django_db
def test_ensure_djstripe_owner_account_links_account_without_refresh(monkeypatch):
    api_key = 'stripe_test_api_key_placeholder'

    class _FakeStripeAccount:
        pass

    account_payload = _FakeStripeAccount()
    account_payload.id = 'acct_test_123'
    account_payload.livemode = False
    account_payload.object = 'account'
    account_payload.settings = {}
    account_payload.to_dict = lambda: {
        'id': 'acct_test_123',
        'livemode': False,
        'object': 'account',
        'settings': {},
    }

    monkeypatch.setattr(
        stripe.Account,
        'retrieve',
        lambda **kwargs: account_payload,
    )

    synced_account = Account(djstripe_id='acct_test_123')

    called = {}

    def fake_sync_from_stripe_data(data, api_key=None):
        called['data'] = data
        called['api_key'] = api_key
        return synced_account

    monkeypatch.setattr(Account, 'sync_from_stripe_data', fake_sync_from_stripe_data)

    api_key_record = APIKey(secret=api_key)
    api_key_record.save = Mock()
    api_key_record.djstripe_owner_account = None
    monkeypatch.setattr(
        APIKey.objects,
        'get_or_create_by_api_key',
        lambda key: (api_key_record, True),
    )

    account = ensure_djstripe_owner_account(api_key)

    assert account is synced_account
    assert called['api_key'] == api_key
    assert isinstance(called['data'], dict)
    assert called['data']['id'] == 'acct_test_123'

    assert api_key_record.djstripe_owner_account == synced_account
    api_key_record.save.assert_called_once_with(update_fields=['djstripe_owner_account'])


@pytest.mark.django_db
def test_sync_from_djstripe_raises_when_plan_mapping_missing(
    test_user,
):
    djstripe_subscription = SimpleNamespace(
        id='sub_test_123',
        customer=SimpleNamespace(subscriber=test_user),
        plan=SimpleNamespace(id='price_missing'),
        status='active',
        cancel_at_period_end=False,
        cancel_at=None,
    )

    with pytest.raises(StripePlanMappingError) as exc_info:
        SubscriptionService.sync_from_djstripe(djstripe_subscription)

    assert exc_info.value.price_id == 'price_missing'
