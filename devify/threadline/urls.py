"""
Threadline API URLs Configuration

This module defines URL patterns for the Threadline application API endpoints.
All endpoints require authentication and follow RESTful conventions.

Public API endpoints:
- settings/: User settings management
- threadlines/: Email messages with attachments (threadlines)
"""

from django.urls import path

from .views import (
    SettingsAPIView,
    SettingsDetailAPIView,
    EmailMessageAPIView,
    EmailMessageDetailAPIView
)

# URL patterns for Threadline API endpoints
urlpatterns = [
    # Settings endpoints
    path('settings', SettingsAPIView.as_view(), name='settings-list'),
    path('settings/<int:pk>', SettingsDetailAPIView.as_view(), name='settings-detail'),

    # Threadlines endpoints (EmailMessage with attachments)
    path('threadlines', EmailMessageAPIView.as_view(), name='threadlines-list'),
    path('threadlines/<int:pk>', EmailMessageDetailAPIView.as_view(), name='threadlines-detail'),
]
