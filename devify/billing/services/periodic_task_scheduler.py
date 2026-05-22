from __future__ import annotations

import json

from django.conf import settings
from django_celery_beat.models import (
    CrontabSchedule,
    PeriodicTask,
    PeriodicTasks,
)


def _parse_cron_expression(
    expression: str,
    error_message: str,
) -> dict[str, str]:
    parts = [part.strip() for part in (expression or '').split()]
    if len(parts) != 5:
        raise ValueError(error_message)

    timezone = getattr(settings, 'CELERY_TIMEZONE', None) or getattr(
        settings,
        'TIME_ZONE',
        None,
    )
    spec = {
        'minute': parts[0],
        'hour': parts[1],
        'day_of_month': parts[2],
        'month_of_year': parts[3],
        'day_of_week': parts[4],
    }
    if timezone:
        spec['timezone'] = timezone
    return spec


def sync_cron_periodic_task(
    *,
    task_name: str,
    task_path: str,
    enabled: bool,
    schedule: str,
    task_kwargs: dict,
    error_message: str,
    queue: str = 'billing',
) -> tuple[bool, int | None]:
    existing = PeriodicTask.objects.filter(name=task_name)

    if not enabled or not schedule:
        deleted = existing.exists()
        existing.delete()
        if deleted:
            PeriodicTasks.update_changed()
        return False, None

    crontab_kwargs = _parse_cron_expression(schedule, error_message)
    crontab, _ = CrontabSchedule.objects.get_or_create(**crontab_kwargs)
    periodic_task, created = PeriodicTask.objects.update_or_create(
        name=task_name,
        defaults={
            'task': task_path,
            'crontab': crontab,
            'interval': None,
            'queue': queue,
            'enabled': True,
            'args': json.dumps([]),
            'kwargs': json.dumps(task_kwargs),
        },
    )
    PeriodicTasks.update_changed()
    return created, periodic_task.id
