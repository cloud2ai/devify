from __future__ import annotations

from types import SimpleNamespace

import pytest

from django_celery_beat.models import PeriodicTask

from billing.services.periodic_task_scheduler import (
    _parse_cron_expression,
    sync_cron_periodic_task,
)


def test_parse_cron_expression_maps_fields_and_timezone(settings):
    settings.CELERY_TIMEZONE = 'Asia/Shanghai'

    result = _parse_cron_expression(
        '0 9 * * 1-5',
        'Invalid cron expression',
    )

    assert result == {
        'minute': '0',
        'hour': '9',
        'day_of_month': '*',
        'month_of_year': '*',
        'day_of_week': '1-5',
        'timezone': 'Asia/Shanghai',
    }


def test_parse_cron_expression_rejects_non_five_field_expression():
    with pytest.raises(ValueError, match='Invalid cron expression'):
        _parse_cron_expression('0 9 * *', 'Invalid cron expression')


@pytest.mark.django_db
def test_sync_cron_periodic_task_creates_and_deletes_task():
    created, task_id = sync_cron_periodic_task(
        task_name='billing-test-task',
        task_path='billing.tasks.example',
        enabled=True,
        schedule='0 9 * * *',
        task_kwargs={'foo': 'bar'},
        error_message='Invalid cron expression',
    )

    assert created is True
    assert task_id is not None
    task = PeriodicTask.objects.get(name='billing-test-task')
    assert task.task == 'billing.tasks.example'
    assert task.enabled is True
    assert task.queue == 'billing'
    assert task.kwargs == '{"foo": "bar"}'

    created, task_id = sync_cron_periodic_task(
        task_name='billing-test-task',
        task_path='billing.tasks.example',
        enabled=False,
        schedule='0 9 * * *',
        task_kwargs={},
        error_message='Invalid cron expression',
    )

    assert created is False
    assert task_id is None
    assert not PeriodicTask.objects.filter(name='billing-test-task').exists()


def test_sync_cron_periodic_task_updates_changed_when_deleted(monkeypatch):
    deleted = {'value': False}

    class FakeQuerySet:
        def exists(self):
            return True

        def delete(self):
            deleted['value'] = True

    class FakePeriodicTaskManager:
        def filter(self, **kwargs):
            return FakeQuerySet()

    class FakePeriodicTasks:
        calls = 0

        @classmethod
        def update_changed(cls):
            cls.calls += 1

    monkeypatch.setattr(
        'billing.services.periodic_task_scheduler.PeriodicTask',
        FakePeriodicTaskManager(),
    )
    monkeypatch.setattr(
        'billing.services.periodic_task_scheduler.PeriodicTasks',
        FakePeriodicTasks,
    )
    monkeypatch.setattr(
        'billing.services.periodic_task_scheduler.CrontabSchedule',
        SimpleNamespace(),
    )

    created, task_id = sync_cron_periodic_task(
        task_name='billing-test-task',
        task_path='billing.tasks.example',
        enabled=False,
        schedule='0 9 * * *',
        task_kwargs={},
        error_message='Invalid cron expression',
    )

    assert created is False
    assert task_id is None
    assert deleted['value'] is True
    assert FakePeriodicTasks.calls == 1
