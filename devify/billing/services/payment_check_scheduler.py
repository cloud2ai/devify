from __future__ import annotations

from dataclasses import dataclass

from billing.services.config_service import (
    DEFAULT_PAYMENT_CHECK_SCHEDULE,
    get_billing_config,
)
from billing.services.periodic_task_scheduler import sync_cron_periodic_task

PAYMENT_CHECK_TASK_NAME = 'billing-payment-check'
PAYMENT_CHECK_TASK_PATH = 'billing.tasks.payment_check'


@dataclass(slots=True)
class PaymentCheckSchedulerResult:
    created: bool
    enabled: bool
    schedule: str = ''
    providers: list[str] | None = None
    task_id: int | None = None

    def as_dict(self) -> dict:
        return {
            'created': self.created,
            'enabled': self.enabled,
            'schedule': self.schedule,
            'providers': self.providers or [],
            'task_id': self.task_id,
        }


def sync_payment_check_periodic_task(config=None) -> dict:
    config = config or get_billing_config()
    providers = [
        str(provider).strip().lower()
        for provider in (config.payment_check_providers or [])
        if str(provider).strip()
    ]
    providers = list(dict.fromkeys(providers))
    schedule = (config.payment_check_schedule or '').strip()
    if not schedule:
        schedule = DEFAULT_PAYMENT_CHECK_SCHEDULE

    if not config.payment_check_enabled or not providers or not schedule:
        sync_cron_periodic_task(
            task_name=PAYMENT_CHECK_TASK_NAME,
            task_path=PAYMENT_CHECK_TASK_PATH,
            enabled=False,
            schedule='',
            task_kwargs={},
            error_message=(
                'Payment check schedule must be a 5-field cron expression'
            ),
        )
        return PaymentCheckSchedulerResult(
            created=False,
            enabled=False,
            schedule=schedule,
            providers=providers,
            task_id=None,
        ).as_dict()

    created, task_id = sync_cron_periodic_task(
        task_name=PAYMENT_CHECK_TASK_NAME,
        task_path=PAYMENT_CHECK_TASK_PATH,
        enabled=True,
        schedule=schedule,
        task_kwargs={
            'providers': providers,
            'mode': 'auto_fix_safe',
        },
        error_message=(
            'Payment check schedule must be a 5-field cron expression'
        ),
    )
    return PaymentCheckSchedulerResult(
        created=created,
        enabled=True,
        schedule=schedule,
        providers=providers,
        task_id=task_id,
    ).as_dict()
