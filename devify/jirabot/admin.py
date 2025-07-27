from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django_json_widget.widgets import JSONEditorWidget
from django import forms

from .models import (
    Settings,
    EmailTask,
    EmailMessage,
    EmailAttachment,
    JiraIssue
)


class SettingsAdminForm(forms.ModelForm):
    """
    Custom admin form for Settings, using JSONEditorWidget for value field.
    """
    class Meta:
        model = Settings
        fields = '__all__'
        widgets = {
            'value': JSONEditorWidget
        }


@admin.register(Settings)
class SettingsAdmin(admin.ModelAdmin):
    """
    Admin interface for user settings
    """
    form = SettingsAdminForm
    list_display = [
        'user', 'key', 'value_preview', 'is_active', 'created_at'
    ]
    list_filter = ['is_active', 'key', 'created_at']
    search_fields = ['user__username', 'key', 'description']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        (_('Basic Information'), {
            'fields': ('user', 'key', 'value', 'description', 'is_active')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def value_preview(self, obj):
        """Show a preview of the JSON value"""
        import json
        try:
            if isinstance(obj.value, dict):
                return json.dumps(obj.value, indent=2)[:100] + '...'
            else:
                return str(obj.value)[:100] + '...'
        except:
            return str(obj.value)[:100] + '...'
    value_preview.short_description = _('Value Preview')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(EmailTask)
class EmailTaskAdmin(admin.ModelAdmin):
    """
    Admin interface for email tasks
    """
    list_display = [
        'id', 'user', 'status', 'emails_processed',
        'emails_created_issues', 'started_at', 'completed_at'
    ]
    list_filter = ['status', 'started_at', 'created_at']
    search_fields = ['user__username', 'error_message']
    readonly_fields = ['created_at']

    fieldsets = (
        (_('Task Information'), {
            'fields': ('user', 'status')
        }),
        (_('Execution Details'), {
            'fields': (
                'started_at', 'completed_at', 'emails_processed',
                'emails_created_issues'
            )
        }),
        (_('Error Information'), {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(EmailMessage)
class EmailMessageAdmin(admin.ModelAdmin):
    """
    Admin interface for email messages
    """
    list_display = [
        'subject', 'user', 'sender', 'status', 'received_at',
        'task', 'has_attachments'
    ]
    list_filter = ['status', 'received_at', 'created_at']
    search_fields = ['subject', 'sender', 'recipients', 'summary_title', 'user__username']
    readonly_fields = [
        'created_at', 'updated_at', 'llm_content'
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
                'summary_title', 'summary_content', 'summary_priority',
                'llm_content'
            )
        }),
        (_('Processing'), {
            'fields': ('status', 'error_message')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def has_attachments(self, obj):
        return obj.attachments.exists()
    has_attachments.boolean = True
    has_attachments.short_description = _('Has Attachments')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'task')


@admin.register(EmailAttachment)
class EmailAttachmentAdmin(admin.ModelAdmin):
    """
    Admin interface for email attachments
    """
    list_display = [
        'filename', 'user', 'email_message', 'content_type',
        'file_size', 'is_image', 'ocr_content', 'created_at'
    ]
    list_filter = ['is_image', 'content_type', 'created_at']
    search_fields = ['filename', 'email_message__subject', 'user__username']
    readonly_fields = ['created_at', 'ocr_content', 'llm_content']

    fieldsets = (
        (_('Attachment Information'), {
            'fields': (
                'user', 'email_message', 'filename', 'content_type',
                'file_size', 'is_image', 'ocr_content', 'llm_content'
            )
        }),
        (_('File Details'), {
            'fields': ('file_path',),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'email_message')


@admin.register(JiraIssue)
class JiraIssueAdmin(admin.ModelAdmin):
    """
    Admin interface for JIRA issues
    """
    list_display = [
        'jira_issue_key', 'user', 'email_message', 'jira_url',
        'created_at', 'updated_at'
    ]
    search_fields = [
        'jira_issue_key', 'email_message__subject', 'user__username'
    ]
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        (_('Issue Information'), {
            'fields': (
                'user', 'email_message', 'jira_issue_key', 'jira_url'
            )
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        """
        Optimize queryset with select_related for user and email_message
        """
        return super().get_queryset(request).select_related(
            'user', 'email_message'
        )
