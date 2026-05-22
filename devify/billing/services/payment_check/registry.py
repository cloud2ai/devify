from __future__ import annotations

from typing import Dict

from .base import PaymentCheckProvider

_PAYMENT_CHECK_PROVIDERS: Dict[str, PaymentCheckProvider] = {}


def register_payment_check_provider(provider: PaymentCheckProvider) -> None:
    if not provider or not getattr(provider, 'name', ''):
        raise ValueError('Payment check provider must define a name')
    _PAYMENT_CHECK_PROVIDERS[provider.name] = provider


def get_payment_check_provider(provider_name: str) -> PaymentCheckProvider:
    provider_name = (provider_name or '').strip().lower()
    try:
        return _PAYMENT_CHECK_PROVIDERS[provider_name]
    except KeyError as exc:
        raise ValueError(
            f'Unsupported payment check provider: {provider_name}'
        ) from exc
