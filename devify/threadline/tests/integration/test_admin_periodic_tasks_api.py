import uuid

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django_celery_beat.models import CrontabSchedule, PeriodicTask
from rest_framework.test import APIClient

from ..fixtures.payloads import build_periodic_tasks_payload

TASK_NAME = "threadline-schedule-email-fetch"
TASK_FUNC = "threadline.tasks.scheduler.schedule_email_fetch"


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username=f"admin-{uuid.uuid4().hex[:8]}",
        email=f"admin-{uuid.uuid4().hex[:8]}@example.com",
        password="adminpass",
    )


@pytest.fixture
def staff_client(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def email_fetch_task_absent():
    """Temporarily remove the periodic task so tests can assert it doesn't exist."""
    existing = (
        PeriodicTask.objects.filter(name=TASK_NAME)
        .select_related("crontab")
        .first()
    )
    saved = None
    if existing:
        saved = {
            "task": existing.task,
            "args": existing.args,
            "kwargs": existing.kwargs,
            "queue": existing.queue,
            "enabled": existing.enabled,
            "crontab": existing.crontab,
            "interval": existing.interval,
        }
        existing.delete()
    yield
    if saved:
        PeriodicTask.objects.get_or_create(name=TASK_NAME, defaults=saved)


@pytest.mark.django_db
@pytest.mark.integration
class TestAdminPeriodicTaskSettingsAPIView:
    def test_patch_updates_existing_task_only(self, staff_client):
        crontab, _ = CrontabSchedule.objects.get_or_create(
            minute="*/5",
            hour="*",
            day_of_month="*",
            month_of_year="*",
            day_of_week="*",
            timezone=getattr(settings, "TIME_ZONE", "UTC"),
        )
        task, _ = PeriodicTask.objects.update_or_create(
            name=TASK_NAME,
            defaults={
                "task": TASK_FUNC,
                "args": "[]",
                "kwargs": "{}",
                "queue": None,
                "enabled": True,
                "crontab": crontab,
                "interval": None,
            },
        )
        original_task_count = PeriodicTask.objects.count()
        original_crontab_count = CrontabSchedule.objects.count()

        response = staff_client.patch(
            "/api/v1/admin/threadline/periodic-tasks/",
            build_periodic_tasks_payload(enabled=False),
            format="json",
        )

        assert response.status_code == 200
        task.refresh_from_db()
        assert task.enabled is False
        assert task.crontab_id == crontab.id
        assert PeriodicTask.objects.count() == original_task_count
        assert CrontabSchedule.objects.count() == original_crontab_count

    def test_patch_rejects_missing_existing_task(self, staff_client, email_fetch_task_absent):
        response = staff_client.patch(
            "/api/v1/admin/threadline/periodic-tasks/",
            build_periodic_tasks_payload(enabled=True, crontab="*/1 * * * *"),
            format="json",
        )

        assert response.status_code == 400
        assert "Periodic task does not exist" in str(response.data)

    def test_patch_rejects_missing_existing_crontab(self, staff_client):
        crontab, _ = CrontabSchedule.objects.get_or_create(
            minute="*/5",
            hour="*",
            day_of_month="*",
            month_of_year="*",
            day_of_week="*",
            timezone=getattr(settings, "TIME_ZONE", "UTC"),
        )
        PeriodicTask.objects.update_or_create(
            name=TASK_NAME,
            defaults={
                "task": TASK_FUNC,
                "args": "[]",
                "kwargs": "{}",
                "queue": None,
                "enabled": True,
                "crontab": crontab,
                "interval": None,
            },
        )

        response = staff_client.patch(
            "/api/v1/admin/threadline/periodic-tasks/",
            build_periodic_tasks_payload(enabled=True, crontab="0 0 1 1 *"),
            format="json",
        )

        assert response.status_code == 400
        assert "Crontab schedule does not exist" in str(response.data)

