from __future__ import annotations

import logging

from django.contrib.auth import get_user_model
from djstripe.models import Customer

User = get_user_model()
logger = logging.getLogger(__name__)


def _customer_match_sources(customer: Customer, user: User) -> list[str]:
    sources: list[str] = []
    if getattr(customer, 'subscriber_id', None) == user.id:
        sources.append('subscriber')

    return sources


def _matching_customers_for_user(user: User) -> list[Customer]:
    customers = list(
        Customer.objects.select_related('subscriber')
        .filter(subscriber=user)
        .distinct()
    )
    customers.sort(
        key=lambda customer: (
            str(getattr(customer, 'id', '')),
        )
    )
    return customers


def summarize_customer_identity_for_user(user: User | None) -> dict:
    if not user:
        return {
            'has_conflict': False,
            'match_count': 0,
            'customer_ids': [],
            'customers': [],
        }

    customers = _matching_customers_for_user(user)
    customer_details = []
    for customer in customers:
        customer_details.append(
            {
                'id': customer.id,
                'subscriber_id': getattr(customer, 'subscriber_id', None),
                'subscriber_username': (
                    customer.subscriber.username
                    if getattr(customer, 'subscriber', None)
                    else ''
                ),
                'match_sources': _customer_match_sources(customer, user),
                'email': getattr(customer, 'email', '') or '',
            }
        )

    return {
        'has_conflict': len(customers) > 1,
        'match_count': len(customers),
        'customer_ids': [customer.id for customer in customers],
        'customers': customer_details,
    }


def resolve_user_for_customer(customer: Customer | object | None):
    if customer is None:
        return None

    subscriber = getattr(customer, 'subscriber', None)
    if subscriber:
        return subscriber
    return None


def resolve_customer_for_user(user):
    if not user:
        return None

    customers = _matching_customers_for_user(user)
    if not customers:
        return None

    if len(customers) > 1:
        logger.warning(
            'Multiple Stripe customers matched user %s: %s',
            user.id,
            [customer.id for customer in customers],
        )
        return None

    customer = customers[0]

    if customer and getattr(customer, 'subscriber_id', None) != user.id:
        customer.subscriber = user
        customer.save(update_fields=['subscriber'])
    return customer
