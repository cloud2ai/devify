"""
Email Task Monitoring Utilities

Provides monitoring and metrics functionality for email tasks.
"""

import logging
from datetime import timedelta
from typing import Dict, List, Optional
from django.utils import timezone
from django.db.models import Count, Q, Avg
from django.core.cache import cache

from threadline.models import EmailTask

logger = logging.getLogger(__name__)


class EmailTaskMonitor:
    """
    Email task monitoring utility

    Provides comprehensive monitoring and metrics for email tasks.
    """

    @staticmethod
    def get_task_metrics() -> Dict:
        """
        Get comprehensive task metrics

        Returns:
            Dictionary containing task metrics
        """
        try:
            now = timezone.now()

            # Basic counts
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

            # Timeout detection (running tasks over TASK_TIMEOUT_MINUTES)
            timeout_threshold = now - timedelta(
                minutes=settings.TASK_TIMEOUT_MINUTES)
            timeout_tasks = EmailTask.objects.filter(
                status=EmailTask.TaskStatus.RUNNING,
                started_at__lt=timeout_threshold
            ).count()

            # Recent activity (last hour)
            recent_threshold = now - timedelta(hours=1)
            recent_tasks = EmailTask.objects.filter(
                created_at__gte=recent_threshold
            ).count()

            # Recent failures
            recent_failed = EmailTask.objects.filter(
                status=EmailTask.TaskStatus.FAILED,
                created_at__gte=recent_threshold
            ).count()

            # Task type breakdown
            type_stats = EmailTask.objects.values('task_type').annotate(
                count=Count('id')
            ).order_by('-count')

            # Status breakdown
            status_stats = EmailTask.objects.values('status').annotate(
                count=Count('id')
            ).order_by('-count')

            # Performance metrics
            completed_with_timing = EmailTask.objects.filter(
                status=EmailTask.TaskStatus.COMPLETED,
                started_at__isnull=False,
                completed_at__isnull=False
            )

            avg_execution_time = None
            if completed_with_timing.exists():
                execution_times = []
                for task in completed_with_timing:
                    if task.started_at and task.completed_at:
                        duration = (task.completed_at - task.started_at).total_seconds()
                        execution_times.append(duration)

                if execution_times:
                    avg_execution_time = sum(execution_times) / len(execution_times)

            return {
                'timestamp': now.isoformat(),
                'basic_counts': {
                    'total_tasks': total_tasks,
                    'running_tasks': running_tasks,
                    'completed_tasks': completed_tasks,
                    'failed_tasks': failed_tasks,
                    'cancelled_tasks': cancelled_tasks,
                    'skipped_tasks': skipped_tasks,
                },
                'health_indicators': {
                    'timeout_tasks': timeout_tasks,
                    'recent_tasks': recent_tasks,
                    'recent_failed_tasks': recent_failed,
                    'success_rate': (
                        completed_tasks / total_tasks * 100
                        if total_tasks > 0 else 0
                    ),
                    'failure_rate': (
                        failed_tasks / total_tasks * 100
                        if total_tasks > 0 else 0
                    ),
                },
                'task_type_breakdown': list(type_stats),
                'status_breakdown': list(status_stats),
                'performance': {
                    'avg_execution_time_seconds': avg_execution_time,
                }
            }

        except Exception as exc:
            logger.error(f"Failed to get task metrics: {exc}")
            return {'error': str(exc)}

    @staticmethod
    def get_task_status_summary() -> Dict:
        """
        Get task status summary for quick monitoring

        Returns:
            Dictionary containing status summary
        """
        try:
            now = timezone.now()

            # Current running tasks
            running_tasks = EmailTask.objects.filter(
                status=EmailTask.TaskStatus.RUNNING
            ).values('id', 'task_type', 'started_at')

            # Check for timeout tasks
            timeout_threshold = now - timedelta(minutes=settings.TASK_TIMEOUT_MINUTES)
            timeout_tasks = [
                task for task in running_tasks
                if task['started_at'] and task['started_at'] < timeout_threshold
            ]

            # Recent failures (last 24 hours)
            recent_threshold = now - timedelta(hours=24)
            recent_failures = EmailTask.objects.filter(
                status=EmailTask.TaskStatus.FAILED,
                created_at__gte=recent_threshold
            ).count()

            # System health status
            health_status = 'healthy'
            if timeout_tasks:
                health_status = 'warning'
            if recent_failures > 10:  # More than 10 failures in 24 hours
                health_status = 'critical'

            return {
                'timestamp': now.isoformat(),
                'health_status': health_status,
                'running_tasks_count': len(running_tasks),
                'timeout_tasks_count': len(timeout_tasks),
                'recent_failures_24h': recent_failures,
                'running_tasks': list(running_tasks),
                'timeout_tasks': timeout_tasks,
            }

        except Exception as exc:
            logger.error(f"Failed to get task status summary: {exc}")
            return {'error': str(exc)}

    @staticmethod
    def get_email_processing_metrics() -> Dict:
        """
        Get email processing specific metrics

        Returns:
            Dictionary containing email processing metrics
        """
        try:
            now = timezone.now()

            # Last 24 hours metrics
            last_24h = now - timedelta(hours=24)

            # Processing stats by task type
            imap_stats = EmailTask.objects.filter(
                task_type='IMAP_EMAIL_FETCH',
                created_at__gte=last_24h
            ).aggregate(
                total_tasks=Count('id'),
                completed_tasks=Count('id', filter=Q(status=EmailTask.TaskStatus.COMPLETED)),
                failed_tasks=Count('id', filter=Q(status=EmailTask.TaskStatus.FAILED)),
            )

            haraka_stats = EmailTask.objects.filter(
                task_type='HARAKA_EMAIL_FETCH',
                created_at__gte=last_24h
            ).aggregate(
                total_tasks=Count('id'),
                completed_tasks=Count('id', filter=Q(status=EmailTask.TaskStatus.COMPLETED)),
                failed_tasks=Count('id', filter=Q(status=EmailTask.TaskStatus.FAILED)),
            )

            # Calculate success rates
            imap_success_rate = (
                imap_stats['completed_tasks'] / imap_stats['total_tasks'] * 100
                if imap_stats['total_tasks'] > 0 else 0
            )

            haraka_success_rate = (
                haraka_stats['completed_tasks'] / haraka_stats['total_tasks'] * 100
                if haraka_stats['total_tasks'] > 0 else 0
            )

            return {
                'timestamp': now.isoformat(),
                'period': 'last_24_hours',
                'imap_processing': {
                    'total_tasks': imap_stats['total_tasks'],
                    'completed_tasks': imap_stats['completed_tasks'],
                    'failed_tasks': imap_stats['failed_tasks'],
                    'success_rate': imap_success_rate,
                },
                'haraka_processing': {
                    'total_tasks': haraka_stats['total_tasks'],
                    'completed_tasks': haraka_stats['completed_tasks'],
                    'failed_tasks': haraka_stats['failed_tasks'],
                    'success_rate': haraka_success_rate,
                },
                'overall': {
                    'total_tasks': imap_stats['total_tasks'] + haraka_stats['total_tasks'],
                    'overall_success_rate': (
                        (imap_stats['completed_tasks'] + haraka_stats['completed_tasks']) /
                        (imap_stats['total_tasks'] + haraka_stats['total_tasks']) * 100
                        if (imap_stats['total_tasks'] + haraka_stats['total_tasks']) > 0 else 0
                    ),
                }
            }

        except Exception as exc:
            logger.error(f"Failed to get email processing metrics: {exc}")
            return {'error': str(exc)}

    @staticmethod
    def get_recent_tasks(limit: int = 10) -> List[Dict]:
        """
        Get recent tasks for monitoring dashboard

        Args:
            limit: Maximum number of tasks to return

        Returns:
            List of recent task dictionaries
        """
        try:
            tasks = EmailTask.objects.order_by('-created_at')[:limit]

            result = []
            for task in tasks:
                task_data = {
                    'id': task.id,
                    'task_id': task.task_id,
                    'task_type': task.task_type,
                    'status': task.status,
                    'created_at': task.created_at.isoformat(),
                    'started_at': task.started_at.isoformat() if task.started_at else None,
                    'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                    'error_message': task.error_message,
                    'details': task.details,
                }
                result.append(task_data)

            return result

        except Exception as exc:
            logger.error(f"Failed to get recent tasks: {exc}")
            return []

    @staticmethod
    def clear_metrics_cache():
        """
        Clear metrics cache
        """
        try:
            cache.delete('email_task_metrics')
            cache.delete('email_task_status_summary')
            cache.delete('email_processing_metrics')
            logger.info("Metrics cache cleared")
        except Exception as exc:
            logger.error(f"Failed to clear metrics cache: {exc}")

    @staticmethod
    def get_cached_metrics(cache_key: str, fetch_func, timeout: int = 300):
        """
        Get cached metrics or fetch fresh data

        Args:
            cache_key: Cache key
            fetch_func: Function to fetch fresh data
            timeout: Cache timeout in seconds

        Returns:
            Cached or fresh metrics data
        """
        try:
            # Try to get from cache first
            cached_data = cache.get(cache_key)
            if cached_data:
                return cached_data

            # Fetch fresh data
            fresh_data = fetch_func()

            # Cache the data
            cache.set(cache_key, fresh_data, timeout)

            return fresh_data

        except Exception as exc:
            logger.error(f"Failed to get cached metrics for {cache_key}: {exc}")
            return {'error': str(exc)}


def get_task_metrics():
    """
    Get task metrics (cached)

    Returns:
        Task metrics dictionary
    """
    monitor = EmailTaskMonitor()
    return monitor.get_cached_metrics(
        'email_task_metrics',
        monitor.get_task_metrics,
        timeout=300  # 5 minutes
    )


def get_task_status_summary():
    """
    Get task status summary (cached)

    Returns:
        Task status summary dictionary
    """
    monitor = EmailTaskMonitor()
    return monitor.get_cached_metrics(
        'email_task_status_summary',
        monitor.get_task_status_summary,
        timeout=60  # 1 minute
    )


def get_email_processing_metrics():
    """
    Get email processing metrics (cached)

    Returns:
        Email processing metrics dictionary
    """
    monitor = EmailTaskMonitor()
    return monitor.get_cached_metrics(
        'email_processing_metrics',
        monitor.get_email_processing_metrics,
        timeout=300  # 5 minutes
    )


def get_monitoring_dashboard_data():
    """
    Get comprehensive monitoring dashboard data

    Returns:
        Complete dashboard data dictionary
    """
    try:
        monitor = EmailTaskMonitor()

        return {
            'task_metrics': get_task_metrics(),
            'status_summary': get_task_status_summary(),
            'processing_metrics': get_email_processing_metrics(),
            'recent_tasks': monitor.get_recent_tasks(20),
            'timestamp': timezone.now().isoformat(),
        }

    except Exception as exc:
        logger.error(f"Failed to get monitoring dashboard data: {exc}")
        return {'error': str(exc)}