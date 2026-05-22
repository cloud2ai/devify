from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import stripe
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from djstripe.models import Customer, Subscription as DjstripeSubscription

from billing.models import PaymentRecord, Subscription
from billing.services.customer_identity import (
    resolve_customer_for_user,
    resolve_user_for_customer,
)
from billing.services.config_service import (
    DEFAULT_PAYMENT_RECORD_BACKFILL_LOOKBACK_DAYS,
    get_stripe_secret_key,
)
from billing.services.subscription_service import SubscriptionService
from billing.services.stripe_compat import stripe_value

logger = logging.getLogger(__name__)
User = get_user_model()


@dataclass(slots=True)
class PaymentRecordSyncResult:
    created: bool
    updated: bool
    skipped: bool
    reason: str = ''
    payment_record_id: int | None = None
    provider_payment_id: str = ''
    user_id: int | None = None
    subscription_id: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            'created': self.created,
            'updated': self.updated,
            'skipped': self.skipped,
            'reason': self.reason,
            'payment_record_id': self.payment_record_id,
            'provider_payment_id': self.provider_payment_id,
            'user_id': self.user_id,
            'subscription_id': self.subscription_id,
        }


_stripe_value = stripe_value


def _normalize_currency(value: Any) -> str:
    currency = str(value or 'USD').strip().upper()
    return currency[:3] if currency else 'USD'


def _resolve_customer_user(customer_id: str) -> tuple[User | None, Customer | None]:
    customer = Customer.objects.select_related('subscriber').filter(
        id=customer_id
    ).first()
    if customer:
        user = resolve_user_for_customer(customer)
        if user:
            return user, customer

    if not customer_id:
        return None, None

    stripe.api_key = get_stripe_secret_key()
    if not stripe.api_key:
        return None, customer

    try:
        stripe_customer = stripe.Customer.retrieve(customer_id)
    except Exception as exc:  # pragma: no cover - network failure path
        logger.warning(
            'Failed to retrieve Stripe customer %s: %s',
            customer_id,
            exc,
        )
        return None, customer

    if customer is not None:
        customer.metadata = _stripe_value(stripe_customer, 'metadata') or {}
        return resolve_user_for_customer(customer), customer

    return None, customer


def _resolve_local_subscription(
    stripe_subscription_id: str | None,
    user: User | None,
    customer: Customer | None,
) -> Subscription | None:
    if stripe_subscription_id:
        djstripe_subscription = DjstripeSubscription.objects.filter(
            id=stripe_subscription_id
        ).select_related('customer').first()
        if djstripe_subscription:
            subscription = Subscription.objects.select_related(
                'user',
                'plan',
                'provider',
            ).filter(djstripe_subscription=djstripe_subscription).first()
            if subscription:
                return subscription

    return None


def _payment_record_metadata(
    invoice: Any,
    *,
    source: str,
    event_type: str | None,
    customer: Customer | None,
    user: User | None,
) -> dict[str, Any]:
    payment_intent_id = _stripe_value(invoice, 'payment_intent')
    if isinstance(payment_intent_id, dict):
        payment_intent_id = payment_intent_id.get('id')
    charge_id = _stripe_value(invoice, 'charge')
    if isinstance(charge_id, dict):
        charge_id = charge_id.get('id')
    return {
        'source': source,
        'event_type': event_type or '',
        'invoice_number': _stripe_value(invoice, 'number') or '',
        'billing_reason': _stripe_value(invoice, 'billing_reason') or '',
        'customer_id': _stripe_value(invoice, 'customer') or '',
        'customer_email': customer.email if customer else '',
        'stripe_customer_user_id': user.id if user else None,
        'subscription_id': _stripe_value(invoice, 'subscription') or '',
        'payment_intent_id': payment_intent_id or '',
        'charge_id': charge_id or '',
        'receipt_number': _stripe_value(invoice, 'receipt_number') or '',
        'invoice_status': _stripe_value(invoice, 'status') or '',
        'paid': bool(_stripe_value(invoice, 'paid', False)),
        'attempt_count': _stripe_value(invoice, 'attempt_count', 0) or 0,
    }


@transaction.atomic
def upsert_payment_record_from_stripe_invoice(
    invoice: Any,
    *,
    source: str,
    event_type: str | None = None,
    status: str = 'succeeded',
) -> PaymentRecordSyncResult:
    invoice_id = _stripe_value(invoice, 'id')
    if not invoice_id:
        raise ValueError('Stripe invoice id is missing')

    customer_id = _stripe_value(invoice, 'customer')
    stripe_subscription_id = _stripe_value(invoice, 'subscription')
    amount_cents = int(
        _stripe_value(invoice, 'amount_paid', _stripe_value(invoice, 'amount_due', 0))
        or 0
    )
    currency = _normalize_currency(_stripe_value(invoice, 'currency'))

    user, customer = _resolve_customer_user(customer_id)
    if not user:
        logger.warning(
            'Skipping payment record sync for invoice %s: unresolved customer %s',
            invoice_id,
            customer_id,
        )
        return PaymentRecordSyncResult(
            created=False,
            updated=False,
            skipped=True,
            reason='unresolved_customer',
            provider_payment_id=invoice_id,
        )

    subscription = _resolve_local_subscription(
        stripe_subscription_id,
        user,
        customer,
    )
    if stripe_subscription_id and not subscription:
        logger.warning(
            'Payment record invoice %s has unresolved subscription %s for customer %s',
            invoice_id,
            stripe_subscription_id,
            customer_id,
        )
    provider = SubscriptionService.get_or_create_payment_provider('stripe')
    metadata = _payment_record_metadata(
        invoice,
        source=source,
        event_type=event_type,
        customer=customer,
        user=user,
    )

    defaults = {
        'user': user,
        'subscription': subscription,
        'provider': provider,
        'amount_cents': amount_cents,
        'currency': currency,
        'status': status,
        'metadata': metadata,
    }
    # NOTE: invoice.id is the idempotency key. Webhook retries and scheduled
    # backfills must converge on the same ledger row instead of duplicating it.
    payment_record, created = PaymentRecord.objects.update_or_create(
        provider_payment_id=invoice_id,
        defaults=defaults,
    )
    return PaymentRecordSyncResult(
        created=created,
        updated=not created,
        skipped=False,
        payment_record_id=payment_record.id,
        provider_payment_id=payment_record.provider_payment_id,
        user_id=payment_record.user_id,
        subscription_id=payment_record.subscription_id,
    )


def _iter_backfill_invoices(
    *,
    lookback_days: int,
    user_id: int | None = None,
    providers: list[str] | None = None,
):
    providers = [
        str(provider or '').strip().lower()
        for provider in (providers or [])
        if str(provider or '').strip()
    ] or ['stripe']
    if 'stripe' not in providers:
        return

    stripe.api_key = get_stripe_secret_key()
    if not stripe.api_key:
        raise ValueError('Stripe secret key is not configured')

    cutoff = timezone.now() - timedelta(days=max(int(lookback_days), 1))
    created_filter = {'gte': int(cutoff.timestamp())}

    if user_id:
        user = User.objects.filter(id=user_id).first()
        if not user:
            return
        customer = resolve_customer_for_user(user)
        customers = []
        if customer:
            customers.append(customer.id)
        for customer_id in dict.fromkeys(customers):
            invoices = stripe.Invoice.list(
                customer=customer_id,
                status='paid',
                created=created_filter,
                limit=100,
            )
            yield from invoices.auto_paging_iter()
        return

    invoices = stripe.Invoice.list(
        status='paid',
        created=created_filter,
        limit=100,
    )
    yield from invoices.auto_paging_iter()


def backfill_payment_records(
    *,
    lookback_days: int | None = None,
    user_id: int | None = None,
    providers: list[str] | None = None,
    source: str = 'manual',
) -> dict[str, Any]:
    window_days = int(
        lookback_days or DEFAULT_PAYMENT_RECORD_BACKFILL_LOOKBACK_DAYS
    )
    normalized_providers = [
        str(provider or '').strip().lower()
        for provider in (providers or [])
        if str(provider or '').strip()
    ] or ['stripe']
    summary = {
        'created': 0,
        'updated': 0,
        'skipped': 0,
        'processed': 0,
        'lookback_days': window_days,
        'user_id': user_id,
        'providers': normalized_providers,
        'source': source,
    }

    for invoice in _iter_backfill_invoices(
        lookback_days=window_days,
        user_id=user_id,
        providers=normalized_providers,
    ):
        summary['processed'] += 1
        result = upsert_payment_record_from_stripe_invoice(
            invoice,
            source=source,
            event_type='backfill',
            status='succeeded',
        )
        if result.skipped:
            summary['skipped'] += 1
        elif result.created:
            summary['created'] += 1
        else:
            summary['updated'] += 1

    return summary
