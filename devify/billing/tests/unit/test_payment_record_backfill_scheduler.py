import json

import pytest

from billing.models import BillingConfig
from billing.services.config_service import (
    DEFAULT_PAYMENT_RECORD_BACKFILL_SCHEDULE,
    get_billing_config,
)
from billing.services.payment_record_backfill_scheduler import (
    PAYMENT_RECORD_BACKFILL_TASK_NAME,
    sync_payment_record_backfill_periodic_task,
)


@pytest.mark.django_db
def test_sync_payment_record_backfill_periodic_task_creates_beat_row():
    config = get_billing_config()
    config.payment_record_backfill = {
        'enabled': True,
        'schedule': '0 */6 * * *',
        'lookback_days': 21,
    }
    config.save(update_fields=['payment_record_backfill'])

    result = sync_payment_record_backfill_periodic_task(config)

    assert result['enabled'] is True
    assert result['schedule'] == '0 */6 * * *'
    assert result['lookback_days'] == 21

    from django_celery_beat.models import PeriodicTask

    task = PeriodicTask.objects.get(name=PAYMENT_RECORD_BACKFILL_TASK_NAME)
    assert task.task == 'billing.tasks.payment_record_backfill'
    assert task.enabled is True
    assert json.loads(task.kwargs) == {
        'lookback_days': 21,
        'providers': ['stripe'],
        'source': 'scheduled_task',
    }


@pytest.mark.django_db
def test_sync_payment_record_backfill_periodic_task_deletes_when_disabled():
    config = get_billing_config()
    config.payment_record_backfill = {
        'enabled': True,
        'schedule': '0 */6 * * *',
        'lookback_days': 21,
    }
    config.save(update_fields=['payment_record_backfill'])
    sync_payment_record_backfill_periodic_task(config)

    config.payment_record_backfill = {
        'enabled': False,
        'schedule': '0 */6 * * *',
        'lookback_days': 21,
    }
    config.save(update_fields=['payment_record_backfill'])

    result = sync_payment_record_backfill_periodic_task(config)

    assert result['enabled'] is False

    from django_celery_beat.models import PeriodicTask

    assert not PeriodicTask.objects.filter(
        name=PAYMENT_RECORD_BACKFILL_TASK_NAME
    ).exists()


@pytest.mark.django_db
def test_sync_payment_record_backfill_periodic_task_uses_default_schedule_when_blank():
    config = BillingConfig.objects.create(
        singleton_key='default',
        payment_record_backfill={
            'enabled': True,
            'schedule': '',
            'lookback_days': 14,
        },
    )

    result = sync_payment_record_backfill_periodic_task(config)

    assert result['enabled'] is True
    assert result['schedule'] == DEFAULT_PAYMENT_RECORD_BACKFILL_SCHEDULE
    assert result['lookback_days'] == 14


@pytest.mark.django_db
def test_sync_payment_record_backfill_periodic_task_maps_standard_cron_fields_correctly():
    config = BillingConfig.objects.create(
        singleton_key='default',
        payment_record_backfill={
            'enabled': True,
            'schedule': '0 9 * * 1-5',
            'lookback_days': 7,
        },
    )

    result = sync_payment_record_backfill_periodic_task(config)

    assert result['enabled'] is True

    from django_celery_beat.models import PeriodicTask

    task = PeriodicTask.objects.get(name=PAYMENT_RECORD_BACKFILL_TASK_NAME)
    assert task.crontab.minute == '0'
    assert task.crontab.hour == '9'
    assert task.crontab.day_of_month == '*'
    assert task.crontab.month_of_year == '*'
    assert task.crontab.day_of_week == '1-5'
