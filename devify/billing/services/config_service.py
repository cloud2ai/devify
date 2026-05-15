from __future__ import annotations

from typing import Any

from django.conf import settings

from billing.models import BillingConfig

MASKED_SECRET_VALUE = '********'
DEFAULT_SINGLETON_KEY = 'default'


def _env_defaults() -> dict[str, Any]:
    return {
        'stripe_live_mode': bool(getattr(settings, 'STRIPE_LIVE_MODE', False)),
        'stripe_publishable_key': getattr(
            settings,
            'STRIPE_PUBLISHABLE_KEY',
            '',
        ),
        'stripe_live_secret_key': getattr(
            settings,
            'STRIPE_LIVE_SECRET_KEY',
            '',
        ),
        'stripe_test_secret_key': getattr(
            settings,
            'STRIPE_TEST_SECRET_KEY',
            '',
        ),
        'stripe_webhook_secret': getattr(
            settings,
            'DJSTRIPE_WEBHOOK_SECRET',
            '',
        ),
        'default_free_credits': int(getattr(settings, 'DEFAULT_FREE_CREDITS', 10)),
        'workflow_cost_credits': int(
            getattr(settings, 'WORKFLOW_COST_CREDITS', 1)
        ),
        'auto_refund_system_errors': bool(
            getattr(settings, 'AUTO_REFUND_SYSTEM_ERRORS', True)
        ),
    }


def get_billing_config() -> BillingConfig:
    config, _ = BillingConfig.objects.get_or_create(
        singleton_key=DEFAULT_SINGLETON_KEY,
        defaults=_env_defaults(),
    )
    return config


def _mask_secret(value: str) -> str:
    return MASKED_SECRET_VALUE if value else ''


def serialize_billing_config(config: BillingConfig | None = None) -> dict[str, Any]:
    config = config or get_billing_config()
    return {
        'id': config.id,
        'singleton_key': config.singleton_key,
        'stripe_live_mode': config.stripe_live_mode,
        'stripe_publishable_key': config.stripe_publishable_key,
        'stripe_live_secret_key': _mask_secret(config.stripe_live_secret_key),
        'stripe_test_secret_key': _mask_secret(config.stripe_test_secret_key),
        'stripe_webhook_secret': _mask_secret(config.stripe_webhook_secret),
        'default_free_credits': config.default_free_credits,
        'workflow_cost_credits': config.workflow_cost_credits,
        'auto_refund_system_errors': config.auto_refund_system_errors,
        'stripe_configured': bool(
            config.stripe_publishable_key
            and (
                config.stripe_live_secret_key
                if config.stripe_live_mode
                else config.stripe_test_secret_key
            )
        ),
        'created_at': config.created_at,
        'updated_at': config.updated_at,
    }


def _preserve_masked_secret(existing: str, incoming: Any) -> str:
    if incoming in (None, ''):
        return existing
    if isinstance(incoming, str) and incoming == MASKED_SECRET_VALUE:
        return existing
    return str(incoming)


def update_billing_config(config: BillingConfig, data: dict[str, Any]) -> BillingConfig:
    config.stripe_live_mode = bool(
        data.get('stripe_live_mode', config.stripe_live_mode)
    )
    config.stripe_publishable_key = data.get(
        'stripe_publishable_key',
        config.stripe_publishable_key,
    ) or ''
    config.stripe_live_secret_key = _preserve_masked_secret(
        config.stripe_live_secret_key,
        data.get('stripe_live_secret_key'),
    )
    config.stripe_test_secret_key = _preserve_masked_secret(
        config.stripe_test_secret_key,
        data.get('stripe_test_secret_key'),
    )
    config.stripe_webhook_secret = _preserve_masked_secret(
        config.stripe_webhook_secret,
        data.get('stripe_webhook_secret'),
    )
    if 'default_free_credits' in data:
        config.default_free_credits = max(
            0,
            int(data.get('default_free_credits') or 0),
        )
    if 'workflow_cost_credits' in data:
        config.workflow_cost_credits = max(
            1,
            int(data.get('workflow_cost_credits') or 1),
        )
    if 'auto_refund_system_errors' in data:
        config.auto_refund_system_errors = bool(
            data.get('auto_refund_system_errors')
        )
    config.save()
    return config


def get_credit_policy() -> dict[str, int]:
    config = get_billing_config()
    return {
        'default_free_credits': config.default_free_credits,
        'workflow_cost_credits': config.workflow_cost_credits,
    }


def get_stripe_publishable_key() -> str:
    return get_billing_config().stripe_publishable_key


def get_stripe_secret_key() -> str:
    config = get_billing_config()
    return (
        config.stripe_live_secret_key
        if config.stripe_live_mode
        else config.stripe_test_secret_key
    )


def get_stripe_webhook_secret() -> str:
    return get_billing_config().stripe_webhook_secret


def get_public_billing_status() -> dict[str, Any]:
    config = get_billing_config()
    return {
        'billing_active': True,
        'provider': 'stripe',
        'stripe_configured': bool(
            config.stripe_publishable_key and get_stripe_secret_key()
        ),
        'stripe_live_mode': config.stripe_live_mode,
        'default_free_credits': config.default_free_credits,
        'workflow_cost_credits': config.workflow_cost_credits,
        'auto_refund_system_errors': config.auto_refund_system_errors,
    }
