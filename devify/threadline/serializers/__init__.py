"""
Threadline Serializers Package

This package contains all serializers for the Threadline application,
organized by model for better maintainability.

Serializers are organized as follows:
- base: Common serializers (UserSerializer)
- settings: Settings model serializers
- email_task: EmailTask model serializers
- email_message: EmailMessage model serializers
- email_attachment: EmailAttachment model serializers
- issue: Issue model serializers
- email_alias: EmailAlias model serializers
- email_todo: EmailTodo model serializers

All serializers are re-exported here for backward compatibility.
"""

# Base serializers
from .base import UserSerializer

# Settings serializers
from .settings import (
    SettingsSerializer,
    SettingsCreateSerializer,
    SettingsUpdateSerializer,
)

# EmailTask serializers
from .email_task import (
    EmailTaskSerializer,
    EmailTaskCreateSerializer,
    EmailTaskUpdateSerializer,
)

# EmailMessage serializers
from .email_message import (
    EmailMessageSerializer,
    EmailMessageListSerializer,
    EmailMessageCreateSerializer,
    EmailMessageUpdateSerializer,
)

# EmailAttachment serializers
from .email_attachment import (
    EmailAttachmentSerializer,
    EmailAttachmentNestedSerializer,
    EmailAttachmentMinimalSerializer,
    EmailAttachmentCreateSerializer,
    EmailAttachmentUpdateSerializer,
)

# Issue serializers
from .issue import (
    IssueSerializer,
    IssueCreateSerializer,
    IssueUpdateSerializer,
)

# EmailAlias serializers
from .email_alias import (
    EmailAliasSerializer,
    EmailAliasCreateSerializer,
)

# EmailTodo serializers
from .email_todo import (
    EmailTodoSerializer,
    EmailTodoListSerializer,
    EmailTodoFilterSerializer,
)

__all__ = [
    # Base
    'UserSerializer',
    # Settings
    'SettingsSerializer',
    'SettingsCreateSerializer',
    'SettingsUpdateSerializer',
    # EmailTask
    'EmailTaskSerializer',
    'EmailTaskCreateSerializer',
    'EmailTaskUpdateSerializer',
    # EmailMessage
    'EmailMessageSerializer',
    'EmailMessageListSerializer',
    'EmailMessageCreateSerializer',
    'EmailMessageUpdateSerializer',
    # EmailAttachment
    'EmailAttachmentSerializer',
    'EmailAttachmentNestedSerializer',
    'EmailAttachmentMinimalSerializer',
    'EmailAttachmentCreateSerializer',
    'EmailAttachmentUpdateSerializer',
    # Issue
    'IssueSerializer',
    'IssueCreateSerializer',
    'IssueUpdateSerializer',
    # EmailAlias
    'EmailAliasSerializer',
    'EmailAliasCreateSerializer',
    # EmailTodo
    'EmailTodoSerializer',
    'EmailTodoListSerializer',
    'EmailTodoFilterSerializer',
]
