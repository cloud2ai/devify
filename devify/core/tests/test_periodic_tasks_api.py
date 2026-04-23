from django.contrib.auth import get_user_model
from django_celery_beat.models import CrontabSchedule, PeriodicTask
from rest_framework.test import APIClient


User = get_user_model()


def _auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _create_crontab(
    minute, hour, day_of_week="*", day_of_month="*", month_of_year="*"
):
    return CrontabSchedule.objects.create(
        minute=minute,
        hour=hour,
        day_of_week=day_of_week,
        day_of_month=day_of_month,
        month_of_year=month_of_year,
        timezone="Asia/Shanghai",
    )


def test_get_periodic_task_settings_includes_existing_database_value(db):
    admin = User.objects.create_user(
        username="admin-user",
        email="admin@example.com",
        password="testpass123",
        is_staff=True,
        is_superuser=True,
    )
    schedule = _create_crontab("*/5", "*")
    PeriodicTask.objects.create(
        name="threadline-schedule-email-fetch",
        task="threadline.tasks.scheduler.schedule_email_fetch",
        args="[]",
        kwargs="{}",
        enabled=False,
        crontab=schedule,
    )

    client = _auth_client(admin)
    response = client.get("/api/v1/admin/periodic-tasks/")

    assert response.status_code == 200
    data = response.json()
    if isinstance(data, dict) and "data" in data:
        data = data["data"]
    data = data["tasks"]
    email_fetch = next(
        item for item in data if item["name"] == "threadline-schedule-email-fetch"
    )
    assert email_fetch["enabled"] is False
    assert email_fetch["crontab"] == "*/5 * * * *"
    assert {item["name"] for item in data} == {
        "threadline-schedule-email-fetch",
        "threadline-reset-stuck-emails",
        "threadline-haraka-cleanup",
        "threadline-email-task-cleanup",
        "threadline-share-link-cleanup",
    }


def test_patch_periodic_task_settings_updates_rows(db):
    admin = User.objects.create_user(
        username="admin-user-2",
        email="admin2@example.com",
        password="testpass123",
        is_staff=True,
        is_superuser=True,
    )

    client = _auth_client(admin)
    response = client.patch(
        "/api/v1/admin/periodic-tasks/",
        data={
            "tasks": [
                {
                    "name": "threadline-haraka-cleanup",
                    "enabled": True,
                    "crontab": "0 1 * * *",
                },
                {
                    "name": "threadline-share-link-cleanup",
                    "enabled": False,
                    "crontab": "10 * * * *",
                },
            ]
        },
        format="json",
    )

    assert response.status_code == 200
    payload = response.json()
    if isinstance(payload, dict) and "data" in payload:
        payload = payload["data"]

    haraka = PeriodicTask.objects.get(name="threadline-haraka-cleanup")
    assert haraka.enabled is True
    assert haraka.crontab.minute == "0"
    assert haraka.crontab.hour == "1"

    share_link = PeriodicTask.objects.get(
        name="threadline-share-link-cleanup"
    )
    assert share_link.enabled is False
    assert share_link.crontab.minute == "10"

    data = payload["tasks"]
    updated = next(
        item for item in data if item["name"] == "threadline-haraka-cleanup"
    )
    assert updated["enabled"] is True
    assert updated["crontab"] == "0 1 * * *"


def test_patch_periodic_task_settings_rejects_invalid_crontab(db):
    admin = User.objects.create_user(
        username="admin-user-3",
        email="admin3@example.com",
        password="testpass123",
        is_staff=True,
        is_superuser=True,
    )

    client = _auth_client(admin)
    response = client.patch(
        "/api/v1/admin/periodic-tasks/",
        data={
            "tasks": [
                {
                    "name": "threadline-share-link-cleanup",
                    "enabled": True,
                    "crontab": "bad cron",
                }
            ]
        },
        format="json",
    )

    assert response.status_code == 400
