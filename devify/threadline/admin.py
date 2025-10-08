"""
Django Admin Configuration for Threadline Application

This module contains optimized Django admin configurations following
best practices. Special attention is given to proper JSON field
handling using django-json-widget.

DJANGO-JSON-WIDGET USAGE GUIDELINES:
=====================================

1. CORRECT USAGE:
   - Use formfield_overrides with JSONEditorWidget
   - Let the widget handle all JSON serialization/deserialization
   - JSONField values are automatically Python objects (dict/list)

2. COMMON MISTAKES TO AVOID:
   - Don't create custom widget classes with overridden methods
   - Don't manually call json.loads() on JSONField values
   - Don't use mark_safe() on JSON strings in widget context
   - Don't override format_value() in custom widgets

3. FOR DISPLAY PURPOSES:
   - Use format_json_preview() function for list view formatting
   - Use separators=(',', ':') for compact JSON display
   - Avoid indent parameter in list views to save space

4. PERFORMANCE OPTIMIZATIONS:
   - Use select_related() for foreign key relationships
   - Use prefetch_related() for many-to-many and reverse foreign
     key relationships
   - Optimize queryset in get_queryset() method

Author: AI Assistant
Last Updated: 2024
"""

import json

from django import forms
from django.contrib import admin
from django.db import models
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django_json_widget.widgets import JSONEditorWidget

from .models import (
    Settings,
    EmailTask,
    EmailAlias,
    EmailMessage,
    EmailAttachment,
    Issue
)


def format_json_preview(value, max_length=100):
    """
    Format JSON value for admin list display with compact format.

    This function handles Django JSONField values for display in admin
    list views. It formats JSON data as compact strings without
    indentation to save space.

    IMPORTANT NOTES:
    - For JSONField, Django automatically converts JSON to Python
      objects (dict/list)
    - Do NOT use json.loads() on JSONField values - they're already
      Python objects
    - Use separators=(',', ':') for compact display without extra spaces
    - Avoid indent parameter to prevent multi-line display in list views

    Args:
        value: The value to format (dict, list, or other types from
               JSONField)
        max_length: Maximum length before truncation (default: 100)

    Returns:
        str: Formatted JSON string for display

    Example:
        Input:  {"name": "test", "value": 123}
        Output: {"name":"test","value":123}
    """
    if not value:
        return '-'

    try:
        if isinstance(value, (dict, list)):
            # Convert Python object to compact JSON string
            # separators=(',', ':') removes extra spaces for compact
            # display
            json_str = json.dumps(
                value, ensure_ascii=False, separators=(',', ':')
            )
        else:
            # Handle non-JSON values (strings, numbers, booleans)
            json_str = str(value)

        return (json_str[:max_length] + '...'
                if len(json_str) > max_length else json_str)
    except (TypeError, ValueError):
        # Fallback for any serialization errors
        return str(value)[:max_length] + '...'


@admin.register(Settings)
class SettingsAdmin(admin.ModelAdmin):
    """Admin interface for Settings model with JSON editor."""

    list_display = [
        'user', 'key', 'value_preview', 'is_active', 'created_at'
    ]
    list_filter = ['is_active', 'key', 'created_at']
    search_fields = ['user__username', 'key', 'description']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        (_('Basic Information'), {
            'fields': (
                'user', 'key', 'value', 'description', 'is_active'
            )
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    # DJANGO-JSON-WIDGET CONFIGURATION FOR SETTINGS
    # This is the CORRECT way to use django-json-widget in Django admin
    #
    # IMPORTANT NOTES:
    # 1. Use formfield_overrides to apply JSONEditorWidget to all
    #    JSONField instances
    # 2. Do NOT create custom widget classes unless absolutely necessary
    # 3. Do NOT override format_value() method - let django-json-widget
    #    handle it
    # 4. The widget automatically handles Python object ↔ JSON string
    #    conversion
    # 5. JavaScript compatibility is handled internally by the widget
    #
    # COMMON MISTAKES TO AVOID:
    # - Don't use custom SafeJSONEditorWidget with overridden methods
    # - Don't manually call json.dumps() in widget methods
    # - Don't use mark_safe() on JSON strings in widget context
    # - Don't create custom ModelForm classes just for JSON widgets
    #
    # This simple configuration provides:
    # - Visual JSON editor in admin forms
    # - Automatic validation
    # - Proper data serialization
    # - JavaScript compatibility
    formfield_overrides = {
        models.JSONField: {'widget': JSONEditorWidget}
    }

    @admin.display(description=_('Value Preview'))
    def value_preview(self, obj):
        """
        Display formatted JSON preview for list view.

        This method shows a compact JSON representation of the
        Settings.value field in the Django admin list view. It uses
        the format_json_preview() function to handle proper formatting.

        IMPORTANT NOTES:
        - obj.value is already a Python object (dict/list) from JSONField
        - Do NOT use json.loads() here - it will cause errors
        - Do NOT use mark_safe() here - it can cause escaping issues
        - The format_json_preview() function handles all formatting

        Args:
            obj: Settings model instance

        Returns:
            str: Formatted JSON string for display in admin list
        """
        return format_json_preview(obj.value)

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('user')


@admin.register(EmailTask)
class EmailTaskAdmin(admin.ModelAdmin):
    """Admin interface for EmailTask model."""

    list_display = [
        'id', 'task_type', 'status', 'created_at'
    ]
    list_filter = ['status', 'task_type', 'created_at']
    search_fields = ['id', 'task_id', 'task_type']
    readonly_fields = ['created_at']

    fieldsets = (
        (_('Task Information'), {
            'fields': ('task_type', 'status', 'task_id')
        }),
        (_('Progress'), {
            'fields': ('started_at', 'completed_at'),
            'classes': ('collapse',)
        }),
        (_('Error Information'), {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
        (_('Details'), {
            'fields': ('details',),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    # JSON widget for details field
    formfield_overrides = {
        models.JSONField: {'widget': JSONEditorWidget}
    }


@admin.register(EmailMessage)
class EmailMessageAdmin(admin.ModelAdmin):
    """Admin interface for EmailMessage model."""

    list_display = [
        'subject_preview', 'user', 'sender', 'status',
        'attachment_count', 'issue_count', 'received_at'
    ]
    list_filter = ['status', 'received_at', 'created_at']
    search_fields = [
        'subject', 'sender', 'recipients', 'summary_title',
        'user__username'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'message_id', 'attachment_links',
        'issue_links'
    ]

    fieldsets = (
        (_('Email Information'), {
            'fields': (
                'user', 'task', 'message_id', 'subject', 'sender',
                'recipients', 'received_at'
            )
        }),
        (_('Content'), {
            'fields': ('raw_content', 'html_content', 'text_content'),
            'classes': ('collapse',)
        }),
        (_('Summary'), {
            'fields': (
                'summary_title', 'summary_content', 'summary_priority'
            ),
            'classes': ('collapse',)
        }),
        (_('LLM Processing'), {
            'fields': ('llm_content',),
            'classes': ('collapse',)
        }),
        (_('Status'), {
            'fields': ('status', 'error_message')
        }),
        (_('Related Objects'), {
            'fields': ('attachment_links', 'issue_links'),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    # DJANGO-JSON-WIDGET CONFIGURATION FOR EMAIL MESSAGE
    # Applies JSONEditorWidget to all JSONField instances
    # (like llm_content)
    # See Settings admin class for detailed configuration notes
    formfield_overrides = {
        models.JSONField: {'widget': JSONEditorWidget}
    }

    @admin.display(description=_('Subject'))
    def subject_preview(self, obj):
        """Display truncated subject."""
        return (obj.subject[:50] + '...'
                if len(obj.subject) > 50 else obj.subject)

    @admin.display(description=_('Attachments'))
    def attachment_count(self, obj):
        """Display attachment count."""
        count = obj.attachments.count()
        return f"{count} 个附件" if count > 0 else "无附件"

    @admin.display(description=_('Issues'))
    def issue_count(self, obj):
        """Display issue count."""
        count = obj.issues.count()
        return f"{count} 个问题" if count > 0 else "无问题"

    @admin.display(description=_('Attachment Links'))
    def attachment_links(self, obj):
        """Display links to related attachments."""
        attachments = obj.attachments.all()
        if not attachments:
            return "无附件"

        links = []
        for attachment in attachments:
            url = reverse(
                'admin:threadline_emailattachment_change',
                args=[attachment.pk]
            )
            link = (f'<a href="{url}" target="_blank">'
                    f'{attachment.filename}</a>')
            links.append(link)

        return mark_safe('<br>'.join(links))

    @admin.display(description=_('Issue Links'))
    def issue_links(self, obj):
        """Display links to related issues."""
        issues = obj.issues.all()
        if not issues:
            return "无问题"

        links = []
        for issue in issues:
            url = reverse(
                'admin:threadline_issue_change', args=[issue.pk]
            )
            link = f'<a href="{url}" target="_blank">{issue.title}</a>'
            if issue.external_id:
                link += f' ({issue.external_id})'
            links.append(link)

        return mark_safe('<br>'.join(links))

    def get_queryset(self, request):
        """Optimize queryset with select_related and prefetch_related."""
        return (super().get_queryset(request)
                .select_related('user', 'task')
                .prefetch_related('attachments', 'issues'))


@admin.register(EmailAttachment)
class EmailAttachmentAdmin(admin.ModelAdmin):
    """Admin interface for EmailAttachment model."""

    list_display = [
        'id', 'filename', 'email_message_link', 'content_type',
        'file_size', 'is_image', 'created_at', 'updated_at'
    ]
    list_filter = ['content_type', 'is_image', 'created_at']
    search_fields = ['filename', 'content_type']
    readonly_fields = [
        'created_at', 'updated_at', 'file_size', 'safe_filename',
        'email_message_link'
    ]

    fieldsets = (
        (_('Attachment Information'), {
            'fields': (
                'user', 'email_message_link', 'filename',
                'safe_filename',
                'content_type', 'file_size', 'is_image'
            )
        }),
        (_('File Storage'), {
            'fields': ('file_path',),
            'classes': ('collapse',)
        }),
        (_('Content'), {
            'fields': ('ocr_content', 'llm_content'),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    # DJANGO-JSON-WIDGET CONFIGURATION FOR EMAIL ATTACHMENT
    # Applies JSONEditorWidget to JSONField instances
    # (like llm_content, ocr_content)
    # See Settings admin class for detailed configuration notes
    formfield_overrides = {
        models.JSONField: {'widget': JSONEditorWidget}
    }

    @admin.display(description=_('Email Message'))
    def email_message_link(self, obj):
        """Display link to related email message."""
        url = reverse(
            'admin:threadline_emailmessage_change',
            args=[obj.email_message.pk]
        )
        subject = (obj.email_message.subject[:30] + '...'
                   if len(obj.email_message.subject) > 30
                   else obj.email_message.subject)
        return mark_safe(
            f'<a href="{url}" target="_blank">{subject}</a>'
        )

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return (super().get_queryset(request)
                .select_related('email_message', 'user'))


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    """Admin interface for Issue model."""

    list_display = [
        'id', 'title', 'email_message_link', 'engine', 'priority',
        'created_at'
    ]
    list_filter = ['engine', 'priority', 'created_at']
    search_fields = [
        'user__username', 'title', 'description', 'external_id'
    ]
    readonly_fields = ['created_at', 'updated_at', 'email_message_link']

    fieldsets = (
        (_('Issue Information'), {
            'fields': (
                'user', 'email_message_link', 'title', 'description'
            )
        }),
        (_('Classification'), {
            'fields': ('priority', 'engine')
        }),
        (_('External System'), {
            'fields': ('external_id', 'issue_url'),
            'classes': ('collapse',)
        }),
        (_('Metadata'), {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    # DJANGO-JSON-WIDGET CONFIGURATION FOR ISSUE
    # Applies JSONEditorWidget to JSONField instances (like metadata)
    # See Settings admin class for detailed configuration notes
    formfield_overrides = {
        models.JSONField: {'widget': JSONEditorWidget}
    }

    @admin.display(description=_('Email Message'))
    def email_message_link(self, obj):
        """Display link to related email message."""
        url = reverse(
            'admin:threadline_emailmessage_change',
            args=[obj.email_message.pk]
        )
        subject = (obj.email_message.subject[:30] + '...'
                   if len(obj.email_message.subject) > 30
                   else obj.email_message.subject)
        return mark_safe(
            f'<a href="{url}" target="_blank">{subject}</a>'
        )

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return (super().get_queryset(request)
                .select_related('user', 'email_message'))


@admin.register(EmailAlias)
class EmailAliasAdmin(admin.ModelAdmin):
    """Admin interface for EmailAlias model"""
    list_display = [
        'alias',
        'user',
        'full_email_address_display',
        'is_active',
        'created_at'
    ]
    list_filter = ['is_active', 'created_at']
    search_fields = ['alias', 'user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at', 'full_email_address_display']
    ordering = ['-created_at']
    list_per_page = 25

    fieldsets = (
        (_('Basic Information'), {
            'fields': ('user', 'alias', 'is_active')
        }),
        (_('Email Address'), {
            'fields': ('full_email_address_display',),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description=_('Domain'))
    def domain_display(self, obj):
        """Display domain for the alias"""
        from django.conf import settings
        return settings.AUTO_ASSIGN_EMAIL_DOMAIN

    def full_email_address_display(self, obj):
        """Display full email address in admin"""
        return obj.full_email_address()
    full_email_address_display.short_description = _('Full Email Address')

    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return (super().get_queryset(request)
                .select_related('user'))


# Admin site customization
admin.site.site_header = _('Threadline Administration')
admin.site.site_title = _('Threadline Admin')
admin.site.index_title = _('Welcome to Threadline Administration')
