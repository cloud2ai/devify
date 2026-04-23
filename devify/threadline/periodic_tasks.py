"""
Register Threadline periodic tasks with the project registry.
"""

from celery.schedules import crontab

from core.periodic_registry import TASK_REGISTRY


def register_periodic_tasks():
    TASK_REGISTRY.add(
        name="threadline-schedule-email-fetch",
        task="threadline.tasks.scheduler.schedule_email_fetch",
        schedule=crontab(minute="*/1"),
    )
    TASK_REGISTRY.add(
        name="threadline-reset-stuck-emails",
        task="threadline.tasks.scheduler.schedule_reset_stuck_emails",
        schedule=crontab(minute="*/30"),
        kwargs={"timeout_minutes": 30},
    )
    TASK_REGISTRY.add(
        name="threadline-haraka-cleanup",
        task="threadline.tasks.scheduler.schedule_haraka_cleanup",
        schedule=crontab(hour=2, minute=0),
    )
    TASK_REGISTRY.add(
        name="threadline-email-task-cleanup",
        task="threadline.tasks.scheduler.schedule_email_task_cleanup",
        schedule=crontab(hour=3, minute=0),
    )
    TASK_REGISTRY.add(
        name="threadline-share-link-cleanup",
        task="threadline.tasks.scheduler.schedule_share_link_cleanup",
        schedule=crontab(minute=10),
    )
