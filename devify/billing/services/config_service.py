from __future__ import annotations

from typing import Any

from django.conf import settings

from billing.models import BillingConfig

MASKED_SECRET_VALUE = '********'
DEFAULT_SINGLETON_KEY = 'default'
DEFAULT_PAYMENT_CHECK_SCHEDULE = '0 2 * * *'
DEFAULT_PAYMENT_RECORD_BACKFILL_SCHEDULE = '0 3 * * *'
DEFAULT_PAYMENT_RECORD_BACKFILL_LOOKBACK_DAYS = 30
PAYMENT_RECORD_BACKFILL_CONFIG_DEFAULT = {
    'enabled': False,
    'schedule': DEFAULT_PAYMENT_RECORD_BACKFILL_SCHEDULE,
    'lookback_days': DEFAULT_PAYMENT_RECORD_BACKFILL_LOOKBACK_DAYS,
    'providers': ['stripe'],
}


def _stripe_configured(config: BillingConfig | None = None) -> bool:
    config = config or get_billing_config()
    return bool(
        config.stripe_publishable_key
        and (
            config.stripe_live_secret_key
            if config.stripe_live_mode
            else config.stripe_test_secret_key
        )
    )


def _normalize_enabled_providers(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        candidates = value.split(',')
    elif isinstance(value, (list, tuple, set)):
        candidates = value
    else:
        return []

    normalized: list[str] = []
    for item in candidates:
        provider = str(item).strip().lower()
        if provider and provider not in normalized:
            normalized.append(provider)
    return normalized


def _env_defaults() -> dict[str, Any]:
    return {
        'stripe_live_mode': False,
        'stripe_publishable_key': '',
        'stripe_live_secret_key': '',
        'stripe_test_secret_key': '',
        'stripe_webhook_secret': '',
        'payment_callback_url': '',
        'self_purchase_enabled': False,
        'payment_check_enabled': False,
        'payment_check_providers': [],
        'payment_check_schedule': DEFAULT_PAYMENT_CHECK_SCHEDULE,
        'payment_record_backfill': dict(
            PAYMENT_RECORD_BACKFILL_CONFIG_DEFAULT
        ),
        'enabled_providers': [],
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


def _normalize_payment_record_backfill_config(
    value: Any,
) -> dict[str, Any]:
    config = dict(PAYMENT_RECORD_BACKFILL_CONFIG_DEFAULT)
    if isinstance(value, dict):
        config['enabled'] = bool(value.get('enabled', False))
        schedule = str(value.get('schedule') or '').strip()
        config['schedule'] = schedule or DEFAULT_PAYMENT_RECORD_BACKFILL_SCHEDULE
        config['lookback_days'] = max(
            int(value.get('lookback_days') or 0),
            1,
        )
        providers = _normalize_enabled_providers(value.get('providers'))
        if providers:
            config['providers'] = providers
    return config


def serialize_billing_config(config: BillingConfig | None = None) -> dict[str, Any]:
    config = config or get_billing_config()
    stripe_configured = _stripe_configured(config)
    payment_check_schedule = (
        (config.payment_check_schedule or '').strip()
        or DEFAULT_PAYMENT_CHECK_SCHEDULE
    )
    payment_record_backfill = _normalize_payment_record_backfill_config(
        getattr(config, 'payment_record_backfill', None)
    )
    return {
        'id': config.id,
        'singleton_key': config.singleton_key,
        'stripe_live_mode': config.stripe_live_mode,
        'stripe_publishable_key': config.stripe_publishable_key,
        'stripe_live_secret_key': _mask_secret(config.stripe_live_secret_key),
        'stripe_test_secret_key': _mask_secret(config.stripe_test_secret_key),
        'stripe_webhook_secret': _mask_secret(config.stripe_webhook_secret),
        'payment_callback_url': config.payment_callback_url,
        'self_purchase_enabled': config.self_purchase_enabled,
        'payment_check_enabled': config.payment_check_enabled,
        'payment_check_providers': config.payment_check_providers or [],
        'payment_check_schedule': payment_check_schedule,
        'payment_record_backfill_enabled': payment_record_backfill['enabled'],
        'payment_record_backfill_schedule': payment_record_backfill['schedule'],
        'payment_record_backfill_lookback_days': (
            payment_record_backfill['lookback_days']
        ),
        'payment_record_backfill_providers': (
            payment_record_backfill['providers']
        ),
        'enabled_providers': config.enabled_providers or [],
        'default_free_credits': config.default_free_credits,
        'workflow_cost_credits': config.workflow_cost_credits,
        'auto_refund_system_errors': config.auto_refund_system_errors,
        'stripe_configured': stripe_configured,
        'recharge_enabled': (
            bool(config.self_purchase_enabled)
            and stripe_configured
            and 'stripe' in (config.enabled_providers or [])
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
    if 'payment_callback_url' in data:
        config.payment_callback_url = (
            str(data.get('payment_callback_url') or '').strip()
        )
    if 'self_purchase_enabled' in data:
        config.self_purchase_enabled = bool(data.get('self_purchase_enabled'))
    if 'payment_check_enabled' in data:
        config.payment_check_enabled = bool(data.get('payment_check_enabled'))
    if 'payment_check_providers' in data:
        config.payment_check_providers = _normalize_enabled_providers(
            data.get('payment_check_providers')
        )
    if 'payment_check_schedule' in data:
        config.payment_check_schedule = (
            str(data.get('payment_check_schedule') or '').strip()
            or DEFAULT_PAYMENT_CHECK_SCHEDULE
        )
    if any(
        key in data
        for key in (
            'payment_record_backfill_enabled',
            'payment_record_backfill_schedule',
            'payment_record_backfill_lookback_days',
            'payment_record_backfill_providers',
        )
    ):
        payment_record_backfill = _normalize_payment_record_backfill_config(
            getattr(config, 'payment_record_backfill', None)
        )
        if 'payment_record_backfill_enabled' in data:
            payment_record_backfill['enabled'] = bool(
                data.get('payment_record_backfill_enabled')
            )
        if 'payment_record_backfill_schedule' in data:
            payment_record_backfill['schedule'] = (
                str(data.get('payment_record_backfill_schedule') or '').strip()
                or DEFAULT_PAYMENT_RECORD_BACKFILL_SCHEDULE
            )
        if 'payment_record_backfill_lookback_days' in data:
            payment_record_backfill['lookback_days'] = max(
                1,
                int(data.get('payment_record_backfill_lookback_days') or 0),
            )
        if 'payment_record_backfill_providers' in data:
            providers = _normalize_enabled_providers(
                data.get('payment_record_backfill_providers')
            )
            if providers:
                payment_record_backfill['providers'] = providers
        config.payment_record_backfill = payment_record_backfill
    if 'enabled_providers' in data:
        config.enabled_providers = _normalize_enabled_providers(
            data.get('enabled_providers')
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


def is_auto_refund_system_errors_enabled() -> bool:
    return bool(get_billing_config().auto_refund_system_errors)


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


def get_payment_callback_url() -> str:
    config = get_billing_config()
    callback_url = (config.payment_callback_url or '').strip()
    if callback_url:
        return callback_url.rstrip('/')
    return getattr(settings, 'FRONTEND_URL', '').rstrip('/')


def get_public_billing_status() -> dict[str, Any]:
    config = get_billing_config()
    stripe_configured = _stripe_configured(config)
    enabled_providers = config.enabled_providers or []
    return {
        'billing_active': True,
        'credits_enabled': True,
        'admin_grant_enabled': True,
        'self_purchase_enabled': config.self_purchase_enabled,
        'enabled_providers': enabled_providers,
        'recharge_enabled': (
            bool(config.self_purchase_enabled)
            and stripe_configured
            and 'stripe' in enabled_providers
        ),
        'provider': 'stripe',
        'stripe_configured': stripe_configured,
        'stripe_live_mode': config.stripe_live_mode,
        'default_free_credits': config.default_free_credits,
        'workflow_cost_credits': config.workflow_cost_credits,
        'auto_refund_system_errors': config.auto_refund_system_errors,
    }
