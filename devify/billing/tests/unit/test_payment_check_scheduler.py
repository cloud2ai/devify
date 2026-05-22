from __future__ import annotations

import json

import pytest

from billing.models import BillingConfig
from billing.services.config_service import (
    DEFAULT_PAYMENT_CHECK_SCHEDULE,
    get_billing_config,
)
from billing.services.payment_check_scheduler import (
    PAYMENT_CHECK_TASK_NAME,
    sync_payment_check_periodic_task,
)


@pytest.mark.django_db
def test_sync_payment_check_periodic_task_creates_beat_row():
    config = get_billing_config()
    config.payment_check_enabled = True
    config.payment_check_providers = ['stripe']
    config.payment_check_schedule = '0 */5 * * *'
    config.save()

    result = sync_payment_check_periodic_task(config)

    assert result['enabled'] is True
    assert result['schedule'] == '0 */5 * * *'
    assert result['providers'] == ['stripe']

    from django_celery_beat.models import PeriodicTask

    task = PeriodicTask.objects.get(name=PAYMENT_CHECK_TASK_NAME)
    assert task.task == 'billing.tasks.payment_check'
    assert task.enabled is True
    assert json.loads(task.kwargs) == {
        'providers': ['stripe'],
        'mode': 'auto_fix_safe',
    }


@pytest.mark.django_db
def test_sync_payment_check_periodic_task_deletes_when_disabled():
    config = get_billing_config()
    config.payment_check_enabled = True
    config.payment_check_providers = ['stripe']
    config.payment_check_schedule = '0 */5 * * *'
    config.save()
    sync_payment_check_periodic_task(config)

    config.payment_check_enabled = False
    config.save(update_fields=['payment_check_enabled'])

    result = sync_payment_check_periodic_task(config)

    assert result['enabled'] is False

    from django_celery_beat.models import PeriodicTask

    assert not PeriodicTask.objects.filter(
        name=PAYMENT_CHECK_TASK_NAME
    ).exists()


@pytest.mark.django_db
def test_sync_payment_check_periodic_task_uses_default_schedule_when_blank():
    from billing.models import PaymentProvider

    PaymentProvider.objects.create(
        name='stripe',
        display_name='Stripe',
        is_active=True,
    )

    config = BillingConfig.objects.create(
        singleton_key='default',
        payment_check_enabled=True,
        payment_check_providers=['stripe'],
        payment_check_schedule='',
    )

    result = sync_payment_check_periodic_task(config)

    assert result['enabled'] is True
    assert result['schedule'] == DEFAULT_PAYMENT_CHECK_SCHEDULE
    assert result['providers'] == ['stripe']

    from django_celery_beat.models import PeriodicTask

    assert PeriodicTask.objects.filter(name=PAYMENT_CHECK_TASK_NAME).exists()


@pytest.mark.django_db
def test_sync_payment_check_periodic_task_maps_standard_cron_fields_correctly():
    from billing.models import PaymentProvider

    PaymentProvider.objects.create(
        name='stripe',
        display_name='Stripe',
        is_active=True,
    )

    config = BillingConfig.objects.create(
        singleton_key='default',
        payment_check_enabled=True,
        payment_check_providers=['stripe'],
        payment_check_schedule='0 2 1 * *',
    )

    result = sync_payment_check_periodic_task(config)

    assert result['enabled'] is True

    from django_celery_beat.models import PeriodicTask

    task = PeriodicTask.objects.get(name=PAYMENT_CHECK_TASK_NAME)
    assert task.crontab.minute == '0'
    assert task.crontab.hour == '2'
    assert task.crontab.day_of_month == '1'
    assert task.crontab.month_of_year == '*'
    assert task.crontab.day_of_week == '*'
