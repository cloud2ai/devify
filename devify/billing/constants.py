from __future__ import annotations

PAYMENT_PROVIDER_NAMES = {
    'stripe': 'stripe',
    'platform': 'platform',
}

PAYMENT_PROVIDER_DISPLAY_NAMES = {
    'stripe': 'Stripe',
    'platform': 'Platform',
}


def normalize_payment_provider_name(provider_name: str | None) -> str:
    return (provider_name or '').strip().lower()


def is_platform_payment_provider(provider_name: str | None) -> bool:
    return normalize_payment_provider_name(provider_name) == 'platform'


def get_payment_provider_display_name(provider_name: str | None) -> str:
    normalized_name = normalize_payment_provider_name(provider_name)
    if not normalized_name:
        return ''
    return PAYMENT_PROVIDER_DISPLAY_NAMES.get(
        normalized_name,
        normalized_name.title(),
    )
