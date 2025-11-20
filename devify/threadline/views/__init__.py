"""
Threadline Views Package

This package contains all APIView classes for the Threadline application,
organized by model for better maintainability.

Public API Views:
- Settings views: SettingsAPIView, SettingsDetailAPIView
- Threadlines views: EmailMessageAPIView, EmailMessageDetailAPIView
  (EmailMessage with attachments exposed as threadlines)
- TODO views: EmailTodoAPIView, EmailTodoDetailAPIView,
  EmailTodoStatsAPIView, EmailTodoBatchAPIView

Internal Views (not exposed in public API):
- EmailTask views: EmailTaskAPIView, EmailTaskDetailAPIView
- EmailAttachment views: EmailAttachmentAPIView, EmailAttachmentDetailAPIView
- Issue views: IssueAPIView, IssueDetailAPIView
"""

from .base import BaseAPIView
from .settings import SettingsAPIView, SettingsDetailAPIView
from .email_message import (
    EmailMessageAPIView,
    EmailMessageDetailAPIView,
    EmailMessageMetadataAPIView,
)
from .email_todo import (
    EmailTodoAPIView,
    EmailTodoDetailAPIView,
    EmailTodoStatsAPIView,
    EmailTodoBatchAPIView,
)

# Internal views (not exposed in public API)
from .email_task import EmailTaskAPIView, EmailTaskDetailAPIView
from .email_attachment import EmailAttachmentAPIView, EmailAttachmentDetailAPIView
from .issue import IssueAPIView, IssueDetailAPIView

__all__ = [
    # Public API views
    'BaseAPIView',
    'SettingsAPIView',
    'SettingsDetailAPIView',
    'EmailMessageAPIView',
    'EmailMessageDetailAPIView',
    'EmailMessageMetadataAPIView',
    'EmailTodoAPIView',
    'EmailTodoDetailAPIView',
    'EmailTodoStatsAPIView',
    'EmailTodoBatchAPIView',

    # Internal views (not exposed in public API)
    'EmailTaskAPIView',
    'EmailTaskDetailAPIView',
    'EmailAttachmentAPIView',
    'EmailAttachmentDetailAPIView',
    'IssueAPIView',
    'IssueDetailAPIView',
]
