from types import SimpleNamespace
from datetime import timedelta

import pytest
from django.utils import timezone

from billing.models import PaymentRecord, Subscription
from billing.services.payment_record_service import (
    backfill_payment_records,
    _resolve_local_subscription,
    upsert_payment_record_from_stripe_invoice,
)
from billing.services.subscription_service import SubscriptionService


@pytest.mark.django_db
def test_upsert_payment_record_from_stripe_invoice_creates_and_updates_record(
    test_user,
    starter_plan,
    mocker,
):
    payment_provider = SubscriptionService.get_or_create_payment_provider(
        'stripe'
    )
    subscription = Subscription.objects.create(
        user=test_user,
        plan=starter_plan,
        provider=payment_provider,
        status='active',
        auto_renew=True,
        current_period_start=timezone.now(),
        current_period_end=timezone.now() + timedelta(days=30),
    )
    invoice = {
        'id': 'in_123',
        'customer': 'cus_123',
        'subscription': 'sub_123',
        'amount_paid': 2999,
        'currency': 'usd',
        'billing_reason': 'subscription_cycle',
        'number': '0001',
        'payment_intent': 'pi_123',
        'charge': 'ch_123',
        'paid': True,
        'attempt_count': 1,
    }

    mocker.patch(
        'billing.services.payment_record_service._resolve_customer_user',
        return_value=(test_user, None),
    )
    mocker.patch(
        'billing.services.payment_record_service._resolve_local_subscription',
        return_value=subscription,
    )

    first = upsert_payment_record_from_stripe_invoice(
        invoice,
        source='webhook',
        event_type='invoice.payment_succeeded',
        status='succeeded',
    )

    assert first.created is True
    assert first.skipped is False
    record = PaymentRecord.objects.get(provider_payment_id='in_123')
    assert record.user == test_user
    assert record.subscription == subscription
    assert record.amount_cents == 2999
    assert record.currency == 'USD'
    assert record.status == 'succeeded'

    invoice['amount_paid'] = 4999
    second = upsert_payment_record_from_stripe_invoice(
        invoice,
        source='webhook',
        event_type='invoice.payment_succeeded',
        status='succeeded',
    )

    assert second.created is False
    record.refresh_from_db()
    assert record.amount_cents == 4999


@pytest.mark.django_db
def test_backfill_payment_records_counts_created_updated_and_skipped(mocker):
    invoice_created = SimpleNamespace(id='in_created')
    invoice_updated = SimpleNamespace(id='in_updated')
    invoice_skipped = SimpleNamespace(id='in_skipped')

    mocker.patch(
        'billing.services.payment_record_service._iter_backfill_invoices',
        return_value=[invoice_created, invoice_updated, invoice_skipped],
    )
    sync_mock = mocker.patch(
        'billing.services.payment_record_service.upsert_payment_record_from_stripe_invoice'
    )
    sync_mock.side_effect = [
        SimpleNamespace(created=True, updated=False, skipped=False),
        SimpleNamespace(created=False, updated=True, skipped=False),
        SimpleNamespace(created=False, updated=False, skipped=True),
    ]

    summary = backfill_payment_records(lookback_days=7, source='manual')

    assert summary['processed'] == 3
    assert summary['created'] == 1
    assert summary['updated'] == 1
    assert summary['skipped'] == 1


@pytest.mark.django_db
def test_resolve_local_subscription_requires_exact_djstripe_match(
    test_user,
    starter_plan,
):
    payment_provider = SubscriptionService.get_or_create_payment_provider(
        'stripe'
    )
    Subscription.objects.create(
        user=test_user,
        plan=starter_plan,
        provider=payment_provider,
        status='active',
        auto_renew=True,
        current_period_start=timezone.now(),
        current_period_end=timezone.now() + timedelta(days=30),
    )

    subscription = _resolve_local_subscription(
        stripe_subscription_id='sub_missing',
        user=test_user,
        customer=None,
    )

    assert subscription is None
