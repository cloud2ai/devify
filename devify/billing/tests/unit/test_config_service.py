import pytest

from billing.services.config_service import (
    MASKED_SECRET_VALUE,
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
        },
    )

    assert updated.default_free_credits == 23
    assert updated.workflow_cost_credits == 2
    assert updated.stripe_live_secret_key == 'sk_live_real_value'


@pytest.mark.django_db
def test_serialize_billing_config_masks_secrets():
    config = get_billing_config()
    config.stripe_publishable_key = 'pk_test_123'
    config.stripe_test_secret_key = 'sk_test_456'
    config.save(
        update_fields=['stripe_publishable_key', 'stripe_test_secret_key']
    )

    serialized = serialize_billing_config(config)

    assert serialized['stripe_publishable_key'] == 'pk_test_123'
    assert serialized['stripe_test_secret_key'] == MASKED_SECRET_VALUE


@pytest.mark.django_db
def test_public_billing_status_is_always_enabled():
    config = get_billing_config()

    status = get_public_billing_status()

    assert status['billing_active'] is True
    assert status['provider'] == 'stripe'
    assert status['default_free_credits'] == config.default_free_credits
