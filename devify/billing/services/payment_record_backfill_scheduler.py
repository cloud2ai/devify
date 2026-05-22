from __future__ import annotations

from dataclasses import dataclass

from billing.services.config_service import (
    DEFAULT_PAYMENT_RECORD_BACKFILL_SCHEDULE,
    get_billing_config,
)
from billing.services.periodic_task_scheduler import sync_cron_periodic_task

PAYMENT_RECORD_BACKFILL_TASK_NAME = 'billing-payment-record-backfill'
PAYMENT_RECORD_BACKFILL_TASK_PATH = 'billing.tasks.payment_record_backfill'


@dataclass(slots=True)
class PaymentRecordBackfillSchedulerResult:
    created: bool
    enabled: bool
    schedule: str = ''
    lookback_days: int = 30
    task_id: int | None = None

    def as_dict(self) -> dict:
        return {
            'created': self.created,
            'enabled': self.enabled,
            'schedule': self.schedule,
            'lookback_days': self.lookback_days,
            'task_id': self.task_id,
        }


def sync_payment_record_backfill_periodic_task(config=None) -> dict:
    config = config or get_billing_config()
    backfill_config = dict(
        getattr(config, 'payment_record_backfill', None) or {}
    )
    schedule = (
        str(backfill_config.get('schedule') or '').strip()
        or DEFAULT_PAYMENT_RECORD_BACKFILL_SCHEDULE
    )
    lookback_days = max(int(backfill_config.get('lookback_days') or 0), 1)
    enabled = bool(backfill_config.get('enabled', False))
    providers = [
        str(provider or '').strip().lower()
        for provider in (backfill_config.get('providers') or [])
        if str(provider or '').strip()
    ] or ['stripe']

    if not enabled or not schedule:
        sync_cron_periodic_task(
            task_name=PAYMENT_RECORD_BACKFILL_TASK_NAME,
            task_path=PAYMENT_RECORD_BACKFILL_TASK_PATH,
            enabled=False,
            schedule='',
            task_kwargs={},
            error_message=(
                'Successful invoice backfill schedule must be a 5-field cron '
                'expression'
            ),
        )
        return PaymentRecordBackfillSchedulerResult(
            created=False,
            enabled=False,
            schedule=schedule,
            lookback_days=lookback_days,
            task_id=None,
        ).as_dict()

    created, task_id = sync_cron_periodic_task(
        task_name=PAYMENT_RECORD_BACKFILL_TASK_NAME,
        task_path=PAYMENT_RECORD_BACKFILL_TASK_PATH,
        enabled=True,
        schedule=schedule,
        task_kwargs={
            'lookback_days': lookback_days,
            'providers': providers,
            'source': 'scheduled_task',
        },
        error_message=(
            'Successful invoice backfill schedule must be a 5-field cron '
            'expression'
        ),
    )
    return PaymentRecordBackfillSchedulerResult(
        created=created,
        enabled=True,
        schedule=schedule,
        lookback_days=lookback_days,
        task_id=task_id,
    ).as_dict()
