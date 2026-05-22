from __future__ import annotations

from datetime import datetime, timezone as dt_timezone

import stripe
from djstripe.models import Customer

from billing.models import Subscription
from billing.services.config_service import (
    get_payment_callback_url,
    get_stripe_secret_key,
)
from billing.services.stripe_compat import stripe_value


class BillingProviderGateway:
    """
    Base interface for billing provider integrations.
    """

    name: str = ''

    def is_configured(self) -> bool:
        return True


class StripeBillingProviderGateway(BillingProviderGateway):
    """
    Stripe billing provider implementation.
    """

    name = 'stripe'

    def is_configured(self) -> bool:
        return bool(get_stripe_secret_key())

    def _customer_idempotency_key(self, user) -> str:
        # Stripe idempotency is what keeps two concurrent customer-creation
        # requests from creating duplicate customers for the same user.
        return f'billing-stripe-customer-{user.id}'

    def _get_existing_customer(self, user):
        customers = list(
            Customer.objects.filter(subscriber=user).order_by('id')
        )
        if len(customers) > 1:
            return {
                'error': 'Multiple Stripe customers found for this user',
            }
        return customers[0] if customers else None

    def _get_or_create_customer(self, user):
        customer = self._get_existing_customer(user)
        if isinstance(customer, dict):
            return customer
        if customer:
            return customer

        stripe.api_key = get_stripe_secret_key()
        stripe_customer = stripe.Customer.create(
            email=getattr(user, 'email', '') or None,
            name=getattr(user, 'get_full_name', lambda: '')() or getattr(
                user,
                'username',
                '',
            ) or None,
            metadata={
                'djstripe_subscriber': str(user.id),
            },
            idempotency_key=self._customer_idempotency_key(user),
        )
        stripe_customer_data = (
            stripe_customer.to_dict()
            if hasattr(stripe_customer, 'to_dict')
            else vars(stripe_customer)
        )
        customer, _ = Customer.objects.update_or_create(
            id=stripe_customer_data['id'],
            defaults={
                'stripe_data': stripe_customer_data,
                'email': stripe_customer_data.get('email') or '',
                'metadata': stripe_customer_data.get('metadata') or {},
                'livemode': stripe_customer_data.get('livemode'),
                'created': datetime.fromtimestamp(
                    stripe_customer_data.get('created') or 0,
                    tz=dt_timezone.utc,
                ),
                'subscriber': user,
            },
        )
        return customer

    def create_checkout_session(self, user, price_id: str) -> dict[str, str]:
        stripe.api_key = get_stripe_secret_key()
        customer = self._get_or_create_customer(user)
        if isinstance(customer, dict):
            return customer
        callback_url = get_payment_callback_url().rstrip('/')

        checkout_session = stripe.checkout.Session.create(
            customer=customer.id,
            payment_method_types=['card'],
            line_items=[
                {
                    'price': price_id,
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url=(
                f'{callback_url}/billing?success=true&'
                f'session_id={{CHECKOUT_SESSION_ID}}'
            ),
            cancel_url=f'{callback_url}/billing?canceled=true',
            metadata={
                'user_id': user.id,
            },
        )

        return {
            'checkout_url': checkout_session.url,
            'session_id': checkout_session.id,
        }

    def create_portal_session(self, user) -> dict[str, str]:
        stripe.api_key = get_stripe_secret_key()
        customer = self._get_existing_customer(user)
        if isinstance(customer, dict):
            return customer
        if not customer:
            return {'error': 'No Stripe customer found for this user'}

        callback_url = get_payment_callback_url().rstrip('/')
        portal_session = stripe.billing_portal.Session.create(
            customer=customer.id,
            return_url=f'{callback_url}/billing',
        )
        return {'portal_url': portal_session.url}

    def schedule_downgrade(
        self,
        current_subscription: Subscription,
        stripe_price_id: str,
    ) -> dict[str, str]:
        if not current_subscription.djstripe_subscription:
            return {'error': 'No active subscription found'}

        stripe.api_key = get_stripe_secret_key()
        djstripe_sub = current_subscription.djstripe_subscription
        stripe_sub = stripe.Subscription.retrieve(djstripe_sub.id)
        items = stripe_value(stripe_sub, 'items')
        item_data = stripe_value(items, 'data', []) or []
        if not item_data:
            return {'error': 'No subscription items found'}
        subscription_item = item_data[0]
        subscription_item_id = stripe_value(subscription_item, 'id')

        stripe.Subscription.modify(
            djstripe_sub.id,
            cancel_at_period_end=False,
            proration_behavior='none',
            items=[{
                'id': subscription_item_id,
                'price': stripe_price_id,
            }],
        )

        effective_date = datetime.fromtimestamp(
            stripe_value(subscription_item, 'current_period_end')
        ).isoformat()
        return {
            'message': 'Downgrade scheduled successfully',
            'effective_date': effective_date,
        }


_GATEWAYS = {
    StripeBillingProviderGateway.name: StripeBillingProviderGateway(),
}


def get_billing_gateway(provider_name: str = 'stripe') -> BillingProviderGateway:
    try:
        return _GATEWAYS[provider_name]
    except KeyError as exc:
        raise ValueError(f'Unsupported billing provider: {provider_name}') from exc
