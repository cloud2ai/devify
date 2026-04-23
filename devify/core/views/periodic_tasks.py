"""Admin API for managing periodic task schedules."""

from __future__ import annotations

import json

from celery.schedules import crontab
from django.conf import settings
from django.db import transaction
from django_celery_beat.models import (
    CrontabSchedule,
    PeriodicTask,
    PeriodicTasks,
)
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import IsAdminUser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


def _is_valid_crontab_expression(expr: str) -> bool:
    if not expr or not str(expr).strip():
        return False
    parts = str(expr).strip().split()
    if len(parts) != 5:
        return False
    try:
        crontab(
            minute=parts[0],
            hour=parts[1],
            day_of_month=parts[2],
            month_of_year=parts[3],
            day_of_week=parts[4],
        )
    except (TypeError, ValueError):
        return False
    return True


def _format_crontab(schedule: CrontabSchedule | None) -> str | None:
    if not schedule:
        return None
    return " ".join(
        [
            schedule.minute,
            schedule.hour,
            schedule.day_of_month,
            schedule.month_of_year,
            schedule.day_of_week,
        ]
    )


def _get_or_create_crontab(expr: str) -> CrontabSchedule:
    parts = str(expr).strip().split()
    timezone = getattr(settings, "TIME_ZONE", "UTC")
    obj, _ = CrontabSchedule.objects.get_or_create(
        minute=parts[0],
        hour=parts[1],
        day_of_month=parts[2],
        month_of_year=parts[3],
        day_of_week=parts[4],
        timezone=timezone,
    )
    return obj


def _task_definitions() -> list[dict]:
    return [
        {
            "name": "threadline-schedule-email-fetch",
            "task": "threadline.tasks.scheduler.schedule_email_fetch",
            "module": "threadline",
            "label": "Email fetch scheduler",
            "description": "Dispatch email fetch jobs on a fixed schedule.",
            "default_enabled": True,
            "default_crontab": "*/1 * * * *",
            "args": (),
            "kwargs": {},
            "queue": None,
        },
        {
            "name": "threadline-reset-stuck-emails",
            "task": "threadline.tasks.scheduler.schedule_reset_stuck_emails",
            "module": "threadline",
            "label": "Stuck email reset",
            "description": "Reset emails that stay stuck for too long.",
            "default_enabled": True,
            "default_crontab": "*/30 * * * *",
            "args": (),
            "kwargs": {"timeout_minutes": 30},
            "queue": None,
        },
        {
            "name": "threadline-haraka-cleanup",
            "task": "threadline.tasks.scheduler.schedule_haraka_cleanup",
            "module": "threadline",
            "label": "Haraka cleanup",
            "description": "Clean up Haraka mail files and old attachments.",
            "default_enabled": True,
            "default_crontab": "0 2 * * *",
            "args": (),
            "kwargs": {},
            "queue": None,
        },
        {
            "name": "threadline-email-task-cleanup",
            "task": "threadline.tasks.scheduler.schedule_email_task_cleanup",
            "module": "threadline",
            "label": "Email task cleanup",
            "description": "Remove old email task records.",
            "default_enabled": True,
            "default_crontab": "0 3 * * *",
            "args": (),
            "kwargs": {},
            "queue": None,
        },
        {
            "name": "threadline-share-link-cleanup",
            "task": "threadline.tasks.scheduler.schedule_share_link_cleanup",
            "module": "threadline",
            "label": "Share link cleanup",
            "description": "Delete expired share links.",
            "default_enabled": True,
            "default_crontab": "10 * * * *",
            "args": (),
            "kwargs": {},
            "queue": None,
        },
    ]


def _resolve_current_definition(definition: dict) -> dict:
    periodic_task = (
        PeriodicTask.objects.select_related("crontab")
        .filter(name=definition["name"])
        .first()
    )
    enabled = (
        periodic_task.enabled
        if periodic_task is not None
        else definition["default_enabled"]
    )
    crontab_value = (
        _format_crontab(periodic_task.crontab)
        if periodic_task and periodic_task.crontab
        else None
    )
    if not crontab_value:
        crontab_value = definition["default_crontab"]
    return {
        "name": definition["name"],
        "task": definition["task"],
        "module": definition["module"],
        "label": definition["label"],
        "description": definition["description"],
        "enabled": bool(enabled),
        "crontab": crontab_value,
        "default_enabled": bool(definition["default_enabled"]),
        "default_crontab": definition["default_crontab"],
    }


def _serialise_tasks() -> list[dict]:
    return [_resolve_current_definition(defn) for defn in _task_definitions()]


def _upsert_task(definition: dict, enabled: bool, crontab_value: str) -> None:
    schedule = _get_or_create_crontab(crontab_value)
    PeriodicTask.objects.update_or_create(
        name=definition["name"],
        defaults={
            "task": definition["task"],
            "args": json.dumps(list(definition["args"])),
            "kwargs": json.dumps(definition["kwargs"]),
            "queue": definition["queue"],
            "enabled": enabled,
            "crontab": schedule,
            "interval": None,
        },
    )


class PeriodicTaskSettingsItemSerializer(serializers.Serializer):
    name = serializers.CharField()
    task = serializers.CharField()
    module = serializers.CharField()
    label = serializers.CharField()
    description = serializers.CharField()
    enabled = serializers.BooleanField()
    crontab = serializers.CharField()
    default_enabled = serializers.BooleanField()
    default_crontab = serializers.CharField()


class PeriodicTaskSettingsUpdateItemSerializer(serializers.Serializer):
    name = serializers.CharField()
    enabled = serializers.BooleanField()
    crontab = serializers.CharField(allow_blank=False)

    def validate_crontab(self, value: str) -> str:
        expr = value.strip()
        if not _is_valid_crontab_expression(expr):
            raise serializers.ValidationError(
                "Invalid 5-field cron expression."
            )
        return expr


class PeriodicTaskSettingsResponseSerializer(serializers.Serializer):
    tasks = PeriodicTaskSettingsItemSerializer(many=True)


class PeriodicTaskSettingsUpdateSerializer(serializers.Serializer):
    tasks = PeriodicTaskSettingsUpdateItemSerializer(many=True)


class AdminPeriodicTaskSettingsAPIView(APIView):
    """List and update the project periodic task schedule settings."""

    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=["admin-periodic-tasks"],
        summary="Get periodic task settings",
        responses={200: PeriodicTaskSettingsResponseSerializer},
    )
    def get(self, request: Request) -> Response:
        return Response({"tasks": _serialise_tasks()})

    @extend_schema(
        tags=["admin-periodic-tasks"],
        summary="Update periodic task settings",
        request=PeriodicTaskSettingsUpdateSerializer,
        responses={200: PeriodicTaskSettingsResponseSerializer},
    )
    def patch(self, request: Request) -> Response:
        serializer = PeriodicTaskSettingsUpdateSerializer(
            data=request.data, partial=False
        )
        serializer.is_valid(raise_exception=True)
        definitions = {item["name"]: item for item in _task_definitions()}
        unknown_names = [
            item["name"]
            for item in serializer.validated_data["tasks"]
            if item["name"] not in definitions
        ]
        if unknown_names:
            return Response(
                {"name": f"Unknown periodic task: {unknown_names[0]}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            for item in serializer.validated_data["tasks"]:
                definition = definitions[item["name"]]
                _upsert_task(
                    definition=definition,
                    enabled=bool(item["enabled"]),
                    crontab_value=item["crontab"],
                )

        PeriodicTasks.update_changed()
        return Response(
            {"tasks": _serialise_tasks()}, status=status.HTTP_200_OK
        )
