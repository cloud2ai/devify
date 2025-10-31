"""
Threadline API URLs Configuration

This module defines URL patterns for the Threadline application API endpoints.
All endpoints require authentication and follow RESTful conventions.

Public API endpoints:
- settings/: User settings management
- settings/email-aliases/: Email alias management for auto-assign mode
- threadlines/: Email messages with attachments (threadlines)
"""

from django.urls import path

from .views import (
    SettingsAPIView,
    SettingsDetailAPIView,
    EmailMessageAPIView,
    EmailMessageDetailAPIView,
    EmailMessageMetadataAPIView
)
from .views.email_alias import (
    EmailAliasAPIView,
    EmailAliasDetailAPIView,
    EmailAliasValidationAPIView
)
from .views.monitoring import (
    task_metrics,
    task_status_summary,
    email_processing_metrics,
    monitoring_dashboard,
    clear_metrics_cache,
    health_check,
    simple_metrics,
    simple_health
)

# URL patterns for Threadline API endpoints
urlpatterns = [
    # Settings endpoints
    path('settings', SettingsAPIView.as_view(), name='settings-list'),
    path('settings/<int:pk>', SettingsDetailAPIView.as_view(),
         name='settings-detail'),

    # Email alias management endpoints (under settings)
    path('settings/email-aliases', EmailAliasAPIView.as_view(),
         name='email-aliases-list'),
    path('settings/email-aliases/<int:alias_id>',
         EmailAliasDetailAPIView.as_view(),
         name='email-aliases-detail'),
    path('settings/email-aliases/validate',
         EmailAliasValidationAPIView.as_view(),
         name='email-aliases-validate'),

    # Threadlines endpoints (EmailMessage with attachments)
    path('threadlines', EmailMessageAPIView.as_view(),
         name='threadlines-list'),
    path('threadlines/<uuid:uuid>', EmailMessageDetailAPIView.as_view(),
         name='threadlines-detail'),
    path('threadlines/<uuid:uuid>/retry',
         EmailMessageDetailAPIView.as_view(),
         name='threadlines-retry'),
    path('threadlines/<uuid:uuid>/metadata',
         EmailMessageMetadataAPIView.as_view(),
         name='threadlines-metadata'),

    # Monitoring endpoints
    # API endpoints (require authentication)
    path('api/task-metrics/', task_metrics, name='task_metrics'),
    path('api/task-status/', task_status_summary, name='task_status_summary'),
    path('api/email-metrics/', email_processing_metrics, name='email_processing_metrics'),
    path('api/dashboard/', monitoring_dashboard, name='monitoring_dashboard'),
    path('api/clear-cache/', clear_metrics_cache, name='clear_metrics_cache'),
    path('api/health/', health_check, name='health_check'),

    # Simple endpoints for external monitoring
    path('metrics/', simple_metrics, name='simple_metrics'),
    path('health/', simple_health, name='simple_health'),
]
