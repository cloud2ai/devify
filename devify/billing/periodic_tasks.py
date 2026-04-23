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
