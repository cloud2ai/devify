"""
Registry for periodic tasks.

Apps register their periodic tasks via `register_periodic_tasks()`, then the
project-level management command writes missing entries to django_celery_beat.
Existing Beat rows are left untouched so manual edits are preserved.
"""

import json
import logging

logger = logging.getLogger(__name__)


def _is_crontab_schedule(schedule):
    return hasattr(schedule, "_orig_minute")


def _get_or_create_crontab(schedule):
    from django.conf import settings
    from django_celery_beat.models import CrontabSchedule

    try:
        obj, created = CrontabSchedule.from_schedule(schedule)
        if created:
            obj.save()
    except (AttributeError, TypeError):
        tz = getattr(schedule, "tz", None) or getattr(
            settings, "CELERY_TIMEZONE", None
        )
        spec = {
            "minute": getattr(schedule, "_orig_minute", "*"),
            "hour": getattr(schedule, "_orig_hour", "*"),
            "day_of_week": getattr(schedule, "_orig_day_of_week", "*"),
            "day_of_month": getattr(schedule, "_orig_day_of_month", "*"),
            "month_of_year": getattr(schedule, "_orig_month_of_year", "*"),
        }
        if tz:
            spec["timezone"] = tz
        obj, _ = CrontabSchedule.objects.get_or_create(**spec)
    return obj


def _get_or_create_interval_seconds(seconds):
    from django_celery_beat.models import IntervalSchedule

    every = max(int(seconds), 1)
    obj, _ = IntervalSchedule.objects.get_or_create(
        every=every,
        period=IntervalSchedule.SECONDS,
    )
    return obj


class TaskRegistry:
    """
    In-memory registry of periodic task definitions.
    """

    def __init__(self):
        self._entries = {}

    def clear(self):
        self._entries.clear()

    def __len__(self):
        return len(self._entries)

    def add(
        self,
        name,
        task,
        schedule,
        args=(),
        kwargs=None,
        queue=None,
        enabled=True,
    ):
        self._entries[name] = {
            "task": task,
            "schedule": schedule,
            "args": tuple(args) if args else (),
            "kwargs": dict(kwargs) if kwargs else {},
            "queue": queue,
            "enabled": enabled,
        }

    def _apply_one(self, name, entry):
        from django_celery_beat.models import PeriodicTask, PeriodicTasks

        task_name = entry["task"]
        schedule = entry["schedule"]
        args = entry["args"]
        kwargs = entry["kwargs"]
        queue = entry["queue"]
        enabled = entry["enabled"]

        if _is_crontab_schedule(schedule):
            crontab_schedule = _get_or_create_crontab(schedule)
            interval_schedule = None
        elif isinstance(schedule, (int, float)):
            interval_schedule = _get_or_create_interval_seconds(schedule)
            crontab_schedule = None
        else:
            run_every = getattr(schedule, "run_every", None)
            if run_every is not None:
                interval_schedule = _get_or_create_interval_seconds(
                    run_every.total_seconds()
                )
                crontab_schedule = None
            else:
                crontab_schedule = _get_or_create_crontab(schedule)
                interval_schedule = None

        create_defaults = {
            "task": task_name,
            "args": json.dumps(list(args)),
            "kwargs": json.dumps(kwargs),
            "queue": queue,
            "enabled": enabled,
        }
        if crontab_schedule is not None:
            create_defaults["crontab"] = crontab_schedule
            create_defaults["interval"] = None
        else:
            create_defaults["interval"] = interval_schedule
            create_defaults["crontab"] = None

        obj, created = PeriodicTask.objects.get_or_create(
            name=name, defaults=create_defaults
        )
        if not created:
            logger.debug(
                "Periodic task already exists, skipping update: %s", name
            )
            return False

        PeriodicTasks.update_changed()
        return True

    def apply(self):
        """
        Write all registered entries to django_celery_beat.
        Existing rows are skipped so database-side edits are preserved.
        """
        for name, entry in self._entries.items():
            try:
                created = self._apply_one(name, entry)
                if created:
                    logger.debug("Registered periodic task: %s", name)
                else:
                    logger.debug("Skipped existing periodic task: %s", name)
            except Exception as e:
                logger.exception(
                    "Failed to register periodic task %s: %s", name, e
                )


TASK_REGISTRY = TaskRegistry()


def apply_registry():
    """Apply the global TASK_REGISTRY to django_celery_beat."""
    TASK_REGISTRY.apply()
