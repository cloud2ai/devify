"""
Task Cleanup Utilities

Provides utilities for cleaning up stale and completed tasks.
"""

import logging
from typing import Dict, List
from django.utils import timezone
from django.db import transaction
from datetime import timedelta

from django.conf import settings

from threadline.models import EmailTask
from threadline.utils.task_tracer import TaskTracer
from .task_lock import force_release_all_locks

logger = logging.getLogger(__name__)


def cleanup_stale_tasks(
    timeout_minutes: int = settings.TASK_TIMEOUT_MINUTES
) -> Dict:
    """
    Clean up stale tasks (RUNNING or PENDING tasks that are too old)

    Returns:
        Cleanup statistics
    """
    try:
        now = timezone.now()
        timeout_threshold = now - timedelta(minutes=timeout_minutes)

        # Find stale tasks
        stale_tasks = EmailTask.objects.filter(
            status__in=[
                EmailTask.TaskStatus.RUNNING,
                EmailTask.TaskStatus.PENDING
            ],
            started_at__lt=timeout_threshold
        )

        cancelled_count = 0
        for task in stale_tasks:
            tracer = TaskTracer(task.task_type)
            tracer.task = task
            tracer.update_task_status(EmailTask.TaskStatus.CANCELLED)
            cancelled_count += 1

        logger.info(
            f"Cleaned up {cancelled_count} stale tasks"
        )

        return {
            'stale_tasks_cancelled': cancelled_count,
            'timeout_threshold': timeout_threshold.isoformat()
        }

    except Exception as exc:
        logger.error(
            f"Failed to cleanup stale tasks: {exc}"
        )
        return {'error': str(exc)}


def startup_cleanup() -> Dict:
    """
    Cleanup tasks on service startup

    Returns:
        Cleanup statistics
    """
    try:
        logger.info("Starting startup cleanup...")

        # 1. Clean up stale tasks
        stale_result = cleanup_stale_tasks()

        # 2. Force release all locks
        force_release_all_locks()

        # 3. Mark any remaining RUNNING tasks as CANCELLED
        running_tasks = EmailTask.objects.filter(
            status=EmailTask.TaskStatus.RUNNING
        )
        cancelled_count = 0

        for task in running_tasks:
            tracer = TaskTracer(task.task_type)
            tracer.task = task
            tracer.update_task_status(EmailTask.TaskStatus.CANCELLED)
            cancelled_count += 1

        logger.info(
            f"Startup cleanup completed: "
            f"{cancelled_count} running tasks cancelled"
        )

        return {
            'stale_tasks_cancelled': stale_result.get(
                'stale_tasks_cancelled', 0
            ),
            'running_tasks_cancelled': cancelled_count,
            'locks_released': True
        }

    except Exception as exc:
        logger.error(f"Startup cleanup failed: {exc}")
        return {'error': str(exc)}


def cleanup_old_tasks(days_old: int = 1) -> Dict:
    """
    Clean up old completed tasks

    Args:
        days_old: Number of days old to consider for cleanup

    Returns:
        Cleanup statistics
    """
    try:
        cutoff_date = timezone.now() - timedelta(days=days_old)

        # Find old completed tasks
        old_tasks = EmailTask.objects.filter(
            status__in=[
                EmailTask.TaskStatus.COMPLETED,
                EmailTask.TaskStatus.FAILED,
                EmailTask.TaskStatus.CANCELLED,
                EmailTask.TaskStatus.SKIPPED
            ],
            completed_at__lt=cutoff_date
        )

        deleted_count = old_tasks.count()

        # Delete old tasks
        with transaction.atomic():
            old_tasks.delete()

        logger.info(
            f"Cleaned up {deleted_count} old tasks "
            f"(older than {days_old} days)"
        )

        return {
            'old_tasks_deleted': deleted_count,
            'cutoff_date': cutoff_date.isoformat()
        }

    except Exception as exc:
        logger.error(
            f"Failed to cleanup old tasks: {exc}"
        )
        return {'error': str(exc)}


def get_task_metrics() -> Dict:
    """
    Get task execution metrics

    Returns:
        Task metrics dictionary
    """
    try:
        now = timezone.now()

        # Basic statistics
        total_tasks = EmailTask.objects.count()
        running_tasks = EmailTask.objects.filter(
            status=EmailTask.TaskStatus.RUNNING
        ).count()
        completed_tasks = EmailTask.objects.filter(
            status=EmailTask.TaskStatus.COMPLETED
        ).count()
        failed_tasks = EmailTask.objects.filter(
            status=EmailTask.TaskStatus.FAILED
        ).count()
        cancelled_tasks = EmailTask.objects.filter(
            status=EmailTask.TaskStatus.CANCELLED
        ).count()
        skipped_tasks = EmailTask.objects.filter(
            status=EmailTask.TaskStatus.SKIPPED
        ).count()

        # Timeout tasks detection (running over TASK_TIMEOUT_MINUTES)
        timeout_threshold = now - timedelta(
            minutes=settings.TASK_TIMEOUT_MINUTES)
        timeout_tasks = EmailTask.objects.filter(
            status=EmailTask.TaskStatus.RUNNING,
            started_at__lt=timeout_threshold
        ).count()

        # Recent failed tasks (last hour)
        recent_failed = EmailTask.objects.filter(
            status=EmailTask.TaskStatus.FAILED,
            created_at__gte=now - timedelta(hours=1)
        ).count()

        return {
            'total_tasks': total_tasks,
            'running_tasks': running_tasks,
            'completed_tasks': completed_tasks,
            'failed_tasks': failed_tasks,
            'cancelled_tasks': cancelled_tasks,
            'skipped_tasks': skipped_tasks,
            'timeout_tasks': timeout_tasks,
            'recent_failed_tasks': recent_failed,
            'timestamp': now.isoformat()
        }

    except Exception as exc:
        logger.error(
            f"Failed to get task metrics: {exc}"
        )
        return {'error': str(exc)}
