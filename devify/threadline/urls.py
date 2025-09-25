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
    EmailMessageDetailAPIView
)
from .views.email_alias import (
    EmailAliasAPIView,
    EmailAliasDetailAPIView,
    EmailAliasValidationAPIView
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
    path('threadlines/<int:pk>', EmailMessageDetailAPIView.as_view(),
         name='threadlines-detail'),
]
