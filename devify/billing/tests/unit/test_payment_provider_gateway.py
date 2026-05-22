from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from billing.services.payment_provider_gateway import (
    StripeBillingProviderGateway,
    get_billing_gateway,
)


def test_get_billing_gateway_returns_stripe_gateway():
    gateway = get_billing_gateway('stripe')

    assert isinstance(gateway, StripeBillingProviderGateway)


def test_get_billing_gateway_rejects_unknown_provider():
    with pytest.raises(ValueError):
        get_billing_gateway('unknown')


def test_stripe_gateway_create_checkout_session(monkeypatch):
    from billing.services import payment_provider_gateway as gateway_module

    gateway = StripeBillingProviderGateway()
    user = SimpleNamespace(id=42)
    customer = SimpleNamespace(id='cus_123')
    session = SimpleNamespace(url='https://checkout.example/session', id='cs_123')
    stripe_create = Mock(return_value=session)

    class FakeQuerySet:
        def __init__(self, results):
            self._results = results

        def order_by(self, *args, **kwargs):
            return self

        def __iter__(self):
            return iter(self._results)

    monkeypatch.setattr(
        gateway_module,
        'get_stripe_secret_key',
        lambda: 'sk_test_123',
    )
    monkeypatch.setattr(
        gateway_module,
        'get_payment_callback_url',
        lambda: 'https://frontend.example',
    )
    monkeypatch.setattr(
        gateway_module.Customer.objects,
        'filter',
        lambda **kwargs: FakeQuerySet([customer]),
    )
    monkeypatch.setattr(
        gateway_module.stripe.checkout.Session,
        'create',
        stripe_create,
    )

    result = gateway.create_checkout_session(user, 'price_123')

    assert result == {
        'checkout_url': 'https://checkout.example/session',
        'session_id': 'cs_123',
    }
    assert stripe_create.called


def test_stripe_gateway_creates_customer_when_missing(monkeypatch):
    from billing.services import payment_provider_gateway as gateway_module

    gateway = StripeBillingProviderGateway()
    user = SimpleNamespace(
        id=42,
        email='user@example.com',
        username='demo-user',
        get_full_name=lambda: 'Demo User',
    )
    created_customer = Mock(id='cus_created', subscriber_id=None)
    session = SimpleNamespace(url='https://checkout.example/session', id='cs_123')
    stripe_customer_create = Mock(return_value=SimpleNamespace(id='cus_123'))
    stripe_create_session = Mock(return_value=session)
    customer_update_or_create = Mock(return_value=(created_customer, True))

    class FakeQuerySet:
        def __init__(self, results):
            self._results = results

        def order_by(self, *args, **kwargs):
            return self

        def __iter__(self):
            return iter(self._results)

    monkeypatch.setattr(
        gateway_module,
        'get_stripe_secret_key',
        lambda: 'sk_test_123',
    )
    monkeypatch.setattr(
        gateway_module,
        'get_payment_callback_url',
        lambda: 'https://frontend.example',
    )
    monkeypatch.setattr(
        gateway_module.Customer.objects,
        'filter',
        lambda **kwargs: FakeQuerySet([]),
    )
    monkeypatch.setattr(
        gateway_module.Customer.objects,
        'update_or_create',
        customer_update_or_create,
    )
    monkeypatch.setattr(
        gateway_module.stripe.Customer,
        'create',
        stripe_customer_create,
    )
    monkeypatch.setattr(
        gateway_module.stripe.checkout.Session,
        'create',
        stripe_create_session,
    )

    result = gateway.create_checkout_session(user, 'price_123')

    assert result == {
        'checkout_url': 'https://checkout.example/session',
        'session_id': 'cs_123',
    }
    stripe_customer_create.assert_called_once_with(
        email='user@example.com',
        name='Demo User',
        metadata={'djstripe_subscriber': '42'},
        idempotency_key='billing-stripe-customer-42',
    )
    customer_update_or_create.assert_called_once()
    stripe_create_session.assert_called_once()


def test_stripe_gateway_create_portal_session_missing_customer(monkeypatch):
    from billing.services import payment_provider_gateway as gateway_module

    gateway = StripeBillingProviderGateway()
    user = SimpleNamespace(id=42)

    class FakeQuerySet:
        def __init__(self, results):
            self._results = results

        def order_by(self, *args, **kwargs):
            return self

        def __iter__(self):
            return iter(self._results)

    monkeypatch.setattr(
        gateway_module,
        'get_stripe_secret_key',
        lambda: 'sk_test_123',
    )
    monkeypatch.setattr(
        gateway_module.Customer.objects,
        'filter',
        lambda **kwargs: FakeQuerySet([]),
    )

    result = gateway.create_portal_session(user)

    assert result == {'error': 'No Stripe customer found for this user'}


def test_stripe_gateway_rejects_multiple_customers(monkeypatch):
    from billing.services import payment_provider_gateway as gateway_module

    gateway = StripeBillingProviderGateway()
    user = SimpleNamespace(id=42)
    customer_one = SimpleNamespace(id='cus_a')
    customer_two = SimpleNamespace(id='cus_b')

    class FakeQuerySet:
        def __init__(self, results):
            self._results = results

        def order_by(self, *args, **kwargs):
            return self

        def __iter__(self):
            return iter(self._results)

    monkeypatch.setattr(
        gateway_module,
        'get_stripe_secret_key',
        lambda: 'sk_test_123',
    )
    monkeypatch.setattr(
        gateway_module.Customer.objects,
        'filter',
        lambda **kwargs: FakeQuerySet([customer_one, customer_two]),
    )

    result = gateway.create_portal_session(user)

    assert result == {'error': 'Multiple Stripe customers found for this user'}


def test_stripe_gateway_checkout_rejects_multiple_customers(monkeypatch):
    from billing.services import payment_provider_gateway as gateway_module

    gateway = StripeBillingProviderGateway()
    user = SimpleNamespace(
        id=42,
        email='user@example.com',
        username='demo-user',
        get_full_name=lambda: 'Demo User',
    )
    customer_one = SimpleNamespace(id='cus_a')
    customer_two = SimpleNamespace(id='cus_b')
    session = SimpleNamespace(url='https://checkout.example/session', id='cs_123')

    class FakeQuerySet:
        def __init__(self, results):
            self._results = results

        def order_by(self, *args, **kwargs):
            return self

        def __iter__(self):
            return iter(self._results)

    monkeypatch.setattr(
        gateway_module,
        'get_stripe_secret_key',
        lambda: 'sk_test_123',
    )
    monkeypatch.setattr(
        gateway_module,
        'get_payment_callback_url',
        lambda: 'https://frontend.example',
    )
    monkeypatch.setattr(
        gateway_module.Customer.objects,
        'filter',
        lambda **kwargs: FakeQuerySet([customer_one, customer_two]),
    )
    monkeypatch.setattr(
        gateway_module.stripe.checkout.Session,
        'create',
        Mock(return_value=session),
    )

    result = gateway.create_checkout_session(user, 'price_123')

    assert result == {'error': 'Multiple Stripe customers found for this user'}


def test_stripe_gateway_schedule_downgrade_handles_stripe_objects(monkeypatch):
    from billing.services import payment_provider_gateway as gateway_module

    gateway = StripeBillingProviderGateway()
    current_subscription = SimpleNamespace(
        djstripe_subscription=SimpleNamespace(id='sub_123'),
    )
    stripe_subscription = SimpleNamespace(
        items=SimpleNamespace(
            data=[
                SimpleNamespace(
                    id='si_123',
                    current_period_end=1712592000,
                )
            ]
        )
    )
    stripe_modify = Mock()

    monkeypatch.setattr(
        gateway_module,
        'get_stripe_secret_key',
        lambda: 'sk_test_123',
    )
    monkeypatch.setattr(
        gateway_module.stripe.Subscription,
        'retrieve',
        Mock(return_value=stripe_subscription),
    )
    monkeypatch.setattr(
        gateway_module.stripe.Subscription,
        'modify',
        stripe_modify,
    )

    result = gateway.schedule_downgrade(current_subscription, 'price_new')

    assert result == {
        'message': 'Downgrade scheduled successfully',
        'effective_date': '2024-04-09T00:00:00',
    }
    stripe_modify.assert_called_once_with(
        'sub_123',
        cancel_at_period_end=False,
        proration_behavior='none',
        items=[{'id': 'si_123', 'price': 'price_new'}],
    )
