"""
Monitoring API Views

Provides REST API endpoints for monitoring email task execution and metrics.
"""

import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from threadline.utils.monitoring import (
    get_task_metrics,
    get_task_status_summary,
    get_email_processing_metrics,
    get_monitoring_dashboard_data,
    EmailTaskMonitor
)

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAdminUser])
@cache_page(60)  # Cache for 1 minute
def task_metrics(request):
    """
    Get email task metrics
    """
    try:
        metrics = get_task_metrics()
        return Response(metrics)

    except Exception as e:
        logger.error(f"Error getting task metrics: {e}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAdminUser])
@cache_page(30)  # Cache for 30 seconds
def task_status_summary(request):
    """
    Get current task status summary
    """
    try:
        summary = get_task_status_summary()
        return Response(summary)

    except Exception as e:
        logger.error(f"Error getting task status summary: {e}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAdminUser])
@cache_page(60)  # Cache for 1 minute
def email_processing_metrics(request):
    """
    Get email processing metrics
    """
    try:
        metrics = get_email_processing_metrics()
        return Response(metrics)

    except Exception as e:
        logger.error(f"Error getting email processing metrics: {e}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAdminUser])
@cache_page(30)  # Cache for 30 seconds
def monitoring_dashboard(request):
    """
    Get comprehensive monitoring dashboard data
    """
    try:
        dashboard_data = get_monitoring_dashboard_data()
        return Response(dashboard_data)

    except Exception as e:
        logger.error(f"Error getting monitoring dashboard: {e}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAdminUser])
def clear_metrics_cache(request):
    """
    Clear monitoring metrics cache
    """
    try:
        monitor = EmailTaskMonitor()
        monitor.clear_metrics_cache()

        return Response({
            'message': 'Metrics cache cleared successfully',
            'timestamp': timezone.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error clearing metrics cache: {e}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def health_check(request):
    """
    Simple health check endpoint
    """
    try:
        summary = get_task_status_summary()

        # Determine health status
        health_status = summary.get('health_status', 'unknown')

        return Response({
            'status': health_status,
            'timestamp': summary.get('timestamp'),
            'running_tasks': summary.get('running_tasks_count', 0),
            'timeout_tasks': summary.get('timeout_tasks_count', 0)
        })

    except Exception as e:
        logger.error(f"Error in health check: {e}")
        return Response(
            {'status': 'error', 'message': 'Health check failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Non-API views for simple JSON responses
@require_http_methods(["GET"])
def simple_metrics(request):
    """
    Simple metrics endpoint for external monitoring tools
    """
    try:
        summary = get_task_status_summary()

        return JsonResponse({
            'running_tasks': summary.get('running_tasks_count', 0),
            'timeout_tasks': summary.get('timeout_tasks_count', 0),
            'recent_failures_24h': summary.get('recent_failures_24h', 0),
            'health_status': summary.get('health_status', 'unknown'),
            'timestamp': summary.get('timestamp')
        })

    except Exception as e:
        logger.error(f"Error in simple metrics: {e}")
        return JsonResponse(
            {'error': 'Internal server error'},
            status=500
        )


@require_http_methods(["GET"])
def simple_health(request):
    """
    Simple health endpoint for load balancers
    """
    try:
        summary = get_task_status_summary()

        # Simple health check
        health_status = summary.get('health_status', 'unknown')
        is_healthy = health_status == 'healthy'

        status_code = 200 if is_healthy else 503

        return JsonResponse(
            {'status': health_status},
            status=status_code
        )

    except Exception as e:
        logger.error(f"Error in simple health check: {e}")
        return JsonResponse(
            {'status': 'error'},
            status=500
        )