import pytest
from django.db import connection

from billing.models import BillingConfig
from billing.services.config_service import (
    MASKED_SECRET_VALUE,
    DEFAULT_PAYMENT_CHECK_SCHEDULE,
    DEFAULT_PAYMENT_RECORD_BACKFILL_LOOKBACK_DAYS,
    DEFAULT_PAYMENT_RECORD_BACKFILL_SCHEDULE,
    get_billing_config,
    get_public_billing_status,
    serialize_billing_config,
    update_billing_config,
)


@pytest.mark.django_db
def test_get_billing_config_creates_singleton_with_defaults():
    config = get_billing_config()

    assert config.singleton_key == 'default'
    assert config.default_free_credits > 0
    assert config.workflow_cost_credits > 0
    assert config.payment_check_enabled is False
    assert config.payment_check_providers == []
    assert config.payment_check_schedule == DEFAULT_PAYMENT_CHECK_SCHEDULE
    assert config.payment_record_backfill == {
        'enabled': False,
        'schedule': DEFAULT_PAYMENT_RECORD_BACKFILL_SCHEDULE,
        'lookback_days': DEFAULT_PAYMENT_RECORD_BACKFILL_LOOKBACK_DAYS,
        'providers': ['stripe'],
    }


@pytest.mark.django_db
def test_update_billing_config_preserves_masked_secret():
    config = get_billing_config()
    config.stripe_live_secret_key = 'sk_live_real_value'
    config.save(update_fields=['stripe_live_secret_key'])

    updated = update_billing_config(
        config,
        {
            'stripe_live_secret_key': MASKED_SECRET_VALUE,
            'default_free_credits': 23,
            'workflow_cost_credits': 2,
            'payment_callback_url': 'http://callback.example',
            'self_purchase_enabled': True,
            'enabled_providers': ['stripe', 'platform'],
            'payment_check_enabled': True,
            'payment_check_providers': ['stripe', 'platform'],
            'payment_check_schedule': '0 */5 * * *',
            'payment_record_backfill_enabled': True,
            'payment_record_backfill_schedule': '0 */6 * * *',
            'payment_record_backfill_lookback_days': 45,
        },
    )

    assert updated.default_free_credits == 23
    assert updated.workflow_cost_credits == 2
    assert updated.payment_callback_url == 'http://callback.example'
    assert updated.stripe_live_secret_key == 'sk_live_real_value'
    assert updated.self_purchase_enabled is True
    assert updated.enabled_providers == ['stripe', 'platform']
    assert updated.payment_check_enabled is True
    assert updated.payment_check_providers == ['stripe', 'platform']
    assert updated.payment_check_schedule == '0 */5 * * *'
    assert updated.payment_record_backfill == {
        'enabled': True,
        'schedule': '0 */6 * * *',
        'lookback_days': 45,
        'providers': ['stripe'],
    }


@pytest.mark.django_db
def test_billing_config_encrypts_stripe_secrets_at_rest():
    config = get_billing_config()
    config.stripe_live_secret_key = 'sk_live_real_value'
    config.stripe_test_secret_key = 'sk_test_real_value'
    config.stripe_webhook_secret = 'whsec_real_value'
    config.save(
        update_fields=[
            'stripe_live_secret_key',
            'stripe_test_secret_key',
            'stripe_webhook_secret',
        ]
    )

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT stripe_live_secret_key, stripe_test_secret_key, stripe_webhook_secret
            FROM billing_config
            WHERE id = %s
            """,
            [config.pk],
        )
        raw_live, raw_test, raw_webhook = cursor.fetchone()

    assert raw_live != 'sk_live_real_value'
    assert raw_test != 'sk_test_real_value'
    assert raw_webhook != 'whsec_real_value'
    assert raw_live.startswith('fernet:')
    assert raw_test.startswith('fernet:')
    assert raw_webhook.startswith('fernet:')

    reloaded = BillingConfig.objects.get(pk=config.pk)
    assert reloaded.stripe_live_secret_key == 'sk_live_real_value'
    assert reloaded.stripe_test_secret_key == 'sk_test_real_value'
    assert reloaded.stripe_webhook_secret == 'whsec_real_value'


@pytest.mark.django_db
def test_update_billing_config_defaults_blank_payment_check_schedule():
    config = get_billing_config()

    updated = update_billing_config(
        config,
        {
            'payment_check_schedule': '   ',
        },
    )

    assert updated.payment_check_schedule == DEFAULT_PAYMENT_CHECK_SCHEDULE


@pytest.mark.django_db
def test_update_billing_config_defaults_blank_payment_record_backfill_schedule():
    config = get_billing_config()

    updated = update_billing_config(
        config,
        {
            'payment_record_backfill_schedule': '   ',
        },
    )

    assert updated.payment_record_backfill == {
        'enabled': False,
        'schedule': DEFAULT_PAYMENT_RECORD_BACKFILL_SCHEDULE,
        'lookback_days': DEFAULT_PAYMENT_RECORD_BACKFILL_LOOKBACK_DAYS,
        'providers': ['stripe'],
    }


@pytest.mark.django_db
def test_serialize_billing_config_masks_secrets():
    config = get_billing_config()
    config.stripe_publishable_key = 'pk_test_123'
    config.stripe_test_secret_key = 'sk_test_456'
    config.payment_callback_url = 'http://callback.example'
    config.self_purchase_enabled = True
    config.enabled_providers = ['stripe']
    config.payment_check_enabled = True
    config.payment_check_providers = ['stripe']
    config.payment_check_schedule = '0 */10 * * *'
    config.payment_record_backfill = {
        'enabled': True,
        'schedule': '0 */12 * * *',
        'lookback_days': 60,
    }
    config.save(
        update_fields=[
            'stripe_publishable_key',
            'stripe_test_secret_key',
            'payment_callback_url',
            'self_purchase_enabled',
            'enabled_providers',
            'payment_check_enabled',
            'payment_check_providers',
            'payment_check_schedule',
            'payment_record_backfill',
        ]
    )

    serialized = serialize_billing_config(config)

    assert serialized['stripe_publishable_key'] == 'pk_test_123'
    assert serialized['stripe_test_secret_key'] == MASKED_SECRET_VALUE
    assert serialized['payment_callback_url'] == 'http://callback.example'
    assert serialized['self_purchase_enabled'] is True
    assert serialized['enabled_providers'] == ['stripe']
    assert serialized['payment_check_enabled'] is True
    assert serialized['payment_check_providers'] == ['stripe']
    assert serialized['payment_check_schedule'] == '0 */10 * * *'
    assert serialized['payment_record_backfill_enabled'] is True
    assert serialized['payment_record_backfill_schedule'] == '0 */12 * * *'
    assert serialized['payment_record_backfill_lookback_days'] == 60
    assert serialized['payment_record_backfill_providers'] == ['stripe']


@pytest.mark.django_db
def test_serialize_billing_config_defaults_blank_payment_check_schedule():
    config = get_billing_config()
    config.payment_check_schedule = ''
    config.save(update_fields=['payment_check_schedule'])

    serialized = serialize_billing_config(config)

    assert serialized['payment_check_schedule'] == DEFAULT_PAYMENT_CHECK_SCHEDULE


@pytest.mark.django_db
def test_serialize_billing_config_defaults_blank_payment_record_backfill_schedule():
    config = get_billing_config()
    config.payment_record_backfill = {
        'enabled': False,
        'schedule': '',
        'lookback_days': DEFAULT_PAYMENT_RECORD_BACKFILL_LOOKBACK_DAYS,
    }
    config.save(update_fields=['payment_record_backfill'])

    serialized = serialize_billing_config(config)

    assert (
        serialized['payment_record_backfill_schedule']
        == DEFAULT_PAYMENT_RECORD_BACKFILL_SCHEDULE
    )
    assert serialized['payment_record_backfill_providers'] == ['stripe']


@pytest.mark.django_db
def test_public_billing_status_is_always_enabled():
    config = get_billing_config()

    status = get_public_billing_status()

    assert status['billing_active'] is True
    assert status['credits_enabled'] is True
    assert status['admin_grant_enabled'] is True
    assert 'recharge_enabled' in status
    assert 'self_purchase_enabled' in status
    assert 'enabled_providers' in status
    assert status['provider'] == 'stripe'
    assert status['default_free_credits'] == config.default_free_credits
