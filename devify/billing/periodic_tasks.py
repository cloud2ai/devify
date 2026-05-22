"""
Register billing periodic tasks with the project registry.
"""
from celery.schedules import crontab

from core.periodic_registry import TASK_REGISTRY


def register_periodic_tasks():
    TASK_REGISTRY.add(
        name="billing-renew-expired-credits",
        task="billing.tasks.renew_expired_credits",
        schedule=crontab(hour=4, minute=0),
    )
    TASK_REGISTRY.add(
        name="billing-downgrade-failed-paid-subscriptions",
        task="billing.tasks.downgrade_failed_paid_subscriptions",
        schedule=crontab(hour=5, minute=0),
    )
    TASK_REGISTRY.add(
        name="billing-payment-check",
        task="billing.tasks.payment_check",
        schedule=crontab(hour="*", minute=0),
        kwargs={
            "mode": "auto_fix_safe",
        },
        enabled=False,
    )
    TASK_REGISTRY.add(
        name="billing-payment-record-backfill",
        task="billing.tasks.payment_record_backfill",
        schedule=crontab(hour=3, minute=0),
        kwargs={
            "source": "scheduled_task",
        },
        enabled=False,
    )
