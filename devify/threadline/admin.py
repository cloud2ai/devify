import json

from django import forms
from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django_json_widget.widgets import JSONEditorWidget

from .models import (
    Settings,
    EmailTask,
    EmailMessage,
    EmailAttachment,
    JiraIssue
)


class SafeJSONEditorWidget(JSONEditorWidget):
    """
    Custom JSON editor widget that safely handles both string and dict values.
    Provides automatic JSON formatting and error handling.
    """

    def value_from_datadict(self, data, files, name):
        """
        Convert form data to Python object with safe JSON parsing.
        """
        value = data.get(name)
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return json.loads(value) if value.strip() else None
            except json.JSONDecodeError:
                return value
        return value

    def value_omitted_from_data(self, data, files, name):
        """
        Check if value is omitted from data.
        """
        return name not in data

    def format_value(self, value):
        """
        Format value for display in widget with proper JSON indentation.
        """
        if value is None:
            return ''
        if isinstance(value, (dict, list)):
            return json.dumps(value, indent=2, ensure_ascii=False)
        if isinstance(value, str):
            try:
                # Try to parse and re-format for consistency
                parsed = json.loads(value)
                return json.dumps(parsed, indent=2, ensure_ascii=False)
            except json.JSONDecodeError:
                return value
        return str(value)


class FormattedTextEditorWidget(forms.Textarea):
    """
    Enhanced text editor widget for fields that may contain JSON or
    formatted text. Provides automatic JSON detection and formatting.
    """

    def render(self, name, value, attrs=None, renderer=None):
        """
        Render the widget with basic JSON formatting.
        """
        # Try to format JSON if the value looks like JSON
        formatted_value = value
        if value and isinstance(value, str):
            try:
                # Check if it looks like JSON
                if (value.strip().startswith('{') or
                    value.strip().startswith('[')):
                    parsed = json.loads(value)
                    formatted_value = json.dumps(
                        parsed, indent=2, ensure_ascii=False
                    )
            except (json.JSONDecodeError, ValueError):
                pass

        # Use default textarea rendering with formatted value
        attrs = attrs or {}
        attrs['rows'] = attrs.get('rows', '10')
        attrs['cols'] = attrs.get('cols', '80')

        return super().render(name, formatted_value, attrs, renderer)


class SettingsAdminForm(forms.ModelForm):
    """
    Custom admin form for Settings, using SafeJSONEditorWidget for
    value field.
    """

    class Meta:
        model = Settings
        fields = '__all__'
        widgets = {
            'value': SafeJSONEditorWidget
        }


class EmailMessageAdminForm(forms.ModelForm):
    """
    Custom admin form for EmailMessage, using FormattedTextEditorWidget
    for content fields.
    """

    class Meta:
        model = EmailMessage
        fields = '__all__'
        widgets = {
            'raw_content': FormattedTextEditorWidget,
            'html_content': FormattedTextEditorWidget,
            'text_content': FormattedTextEditorWidget,
            'llm_content': FormattedTextEditorWidget,
            'error_message': FormattedTextEditorWidget
        }


class EmailAttachmentAdminForm(forms.ModelForm):
    """
    Custom admin form for EmailAttachment, using FormattedTextEditorWidget
    for content fields.
    """

    class Meta:
        model = EmailAttachment
        fields = '__all__'
        widgets = {
            'ocr_content': FormattedTextEditorWidget,
            'llm_content': FormattedTextEditorWidget
        }


@admin.register(Settings)
class SettingsAdmin(admin.ModelAdmin):
    """
    Admin interface for user settings with JSON value formatting.
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
        """
        Show a preview of the JSON value with proper formatting.
        """
        try:
            if isinstance(obj.value, dict):
                formatted_json = json.dumps(
                    obj.value, indent=2, ensure_ascii=False
                )
                if len(formatted_json) > 100:
                    return formatted_json[:100] + '...'
                else:
                    return formatted_json
            else:
                return str(obj.value)[:100] + '...'
        except Exception:
            return str(obj.value)[:100] + '...'

    value_preview.short_description = _('Value Preview')

    def get_queryset(self, request):
        """
        Optimize queryset with select_related for user.
        """
        return super().get_queryset(request).select_related('user')


@admin.register(EmailTask)
class EmailTaskAdmin(admin.ModelAdmin):
    """
    Admin interface for email tasks with comprehensive task management.
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
        """
        Optimize queryset with select_related for user.
        """
        return super().get_queryset(request).select_related('user')


@admin.register(EmailMessage)
class EmailMessageAdmin(admin.ModelAdmin):
    """
    Admin interface for email messages with content formatting and
    attachment management.
    """

    form = EmailMessageAdminForm
    list_display = [
        'subject', 'user', 'sender', 'status', 'received_at',
        'task', 'attachment_count', 'has_attachments'
    ]
    list_filter = ['status', 'received_at', 'created_at']
    search_fields = [
        'subject', 'sender', 'recipients', 'summary_title',
        'user__username'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'llm_content_formatted',
        'raw_content_formatted', 'attachment_details'
    ]

    fieldsets = (
        (_('Email Information'), {
            'fields': (
                'user', 'task', 'message_id', 'subject', 'sender',
                'recipients', 'received_at'
            )
        }),
        (_('Content'), {
            'fields': ('raw_content_formatted', 'html_content', 'text_content'),
            'classes': ('collapse',)
        }),
        (_('Summary'), {
            'fields': (
                'summary_title', 'summary_content', 'summary_priority',
                'llm_content_formatted'
            )
        }),
        (_('Processing'), {
            'fields': ('status', 'error_message')
        }),
        (_('Attachments'), {
            'fields': ('attachment_details',),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def attachment_count(self, obj):
        """
        Display attachment count in list view.
        """
        return obj.attachments.count()
    attachment_count.short_description = _('Attachments')

    def has_attachments(self, obj):
        """
        Check if email message has attachments.
        """
        return obj.attachments.exists()

    has_attachments.boolean = True
    has_attachments.short_description = _('Has Attachments')

    def attachment_details(self, obj):
        """
        Display detailed attachment list in detail view.
        """
        attachments = obj.attachments.all()
        if attachments:
            html = (
                '<h3>Attachment List</h3>'
                '<table style="width: 100%; border-collapse: collapse;">'
                '<thead>'
                '<tr style="background-color: #f5f5f5;">'
                '<th style="border: 1px solid #ddd; padding: 8px; text-align: left;">'
                'Original Filename</th>'
                '<th style="border: 1px solid #ddd; padding: 8px; text-align: left;">'
                'Safe Filename (UUID)</th>'
                '<th style="border: 1px solid #ddd; padding: 8px; text-align: left;">'
                'Content Type</th>'
                '<th style="border: 1px solid #ddd; padding: 8px; text-align: left;">'
                'Size (bytes)</th>'
                '<th style="border: 1px solid #ddd; padding: 8px; text-align: left;">'
                'Type</th>'
                '</tr>'
                '</thead>'
                '<tbody>'
            )
            for attachment in attachments:
                safe_filename = attachment.safe_filename or 'Not set'
                file_type = 'Image' if attachment.is_image else 'File'
                html += (
                    f'<tr>'
                    f'<td style="border: 1px solid #ddd; padding: 8px;">'
                    f'<strong>{attachment.filename}</strong></td>'
                    f'<td style="border: 1px solid #ddd; padding: 8px; '
                    f'font-family: monospace; font-size: 12px;">{safe_filename}</td>'
                    f'<td style="border: 1px solid #ddd; padding: 8px;">'
                    f'{attachment.content_type}</td>'
                    f'<td style="border: 1px solid #ddd; padding: 8px;">'
                    f'{attachment.file_size}</td>'
                    f'<td style="border: 1px solid #ddd; padding: 8px;">'
                    f'{file_type}</td>'
                    f'</tr>'
                )
            html += '</tbody></table>'
            return mark_safe(html)
        return "No attachments"

    attachment_details.short_description = _(
        'Attachment Details'
    )

    def ocr_content_formatted(self, obj):
        """
        Format OCR content for better display.
        """
        if not obj.ocr_content:
            return '-'
        return str(obj.ocr_content)

    ocr_content_formatted.short_description = _('OCR Content (Formatted)')

    def llm_content_formatted(self, obj):
        """
        Format LLM content for better display with JSON formatting.
        """
        if not obj.llm_content:
            return '-'

        try:
            # Try to parse as JSON
            if isinstance(obj.llm_content, str):
                content = json.loads(obj.llm_content)
            else:
                content = obj.llm_content

            return json.dumps(content, indent=2, ensure_ascii=False)
        except (json.JSONDecodeError, TypeError):
            # If not JSON, display as formatted text
            return str(obj.llm_content)

    llm_content_formatted.short_description = _('LLM Content (Formatted)')

    def raw_content_formatted(self, obj):
        """
        Format raw content for better display with JSON formatting.
        """
        if not obj.raw_content:
            return '-'

        try:
            # Try to parse as JSON
            if isinstance(obj.raw_content, str):
                content = json.loads(obj.raw_content)
            else:
                content = obj.raw_content

            return json.dumps(content, indent=2, ensure_ascii=False)
        except (json.JSONDecodeError, TypeError):
            # If not JSON, display as formatted text
            return str(obj.raw_content)

    raw_content_formatted.short_description = _('Raw Content (Formatted)')

    def get_queryset(self, request):
        """
        Optimize queryset with select_related for user and task.
        """
        return super().get_queryset(request).select_related('user', 'task')


@admin.register(EmailAttachment)
class EmailAttachmentAdmin(admin.ModelAdmin):
    """
    Admin interface for email attachments with content formatting and
    file management.
    """

    form = EmailAttachmentAdminForm
    list_display = [
        'filename', 'safe_filename', 'user', 'email_message', 'content_type',
        'file_size', 'is_image', 'status', 'created_at'
    ]
    list_filter = ['status', 'is_image', 'content_type', 'created_at']
    search_fields = [
        'filename', 'safe_filename', 'email_message__subject', 'user__username'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'ocr_content_formatted', 'llm_content_formatted'
    ]

    fieldsets = (
        (_('Attachment Information'), {
            'fields': (
                'user', 'email_message', 'filename', 'safe_filename',
                'content_type', 'file_size', 'is_image'
            )
        }),
        (_('Processing Status'), {
            'fields': ('status', 'error_message'),
        }),
        (_('Content'), {
            'fields': ('ocr_content_formatted', 'llm_content_formatted'),
            'classes': ('collapse',)
        }),
        (_('File Details'), {
            'fields': ('file_path',),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def llm_content_formatted(self, obj):
        """
        Format LLM content for better display with JSON formatting.
        """
        if not obj.llm_content:
            return '-'

        try:
            # Try to parse as JSON
            if isinstance(obj.llm_content, str):
                content = json.loads(obj.llm_content)
            else:
                content = obj.llm_content

            return json.dumps(content, indent=2, ensure_ascii=False)
        except (json.JSONDecodeError, TypeError):
            # If not JSON, display as formatted text
            return str(obj.llm_content)

    llm_content_formatted.short_description = _('LLM Content (Formatted)')

    def ocr_content_formatted(self, obj):
        """
        Format OCR content for better display.
        """
        if not obj.ocr_content:
            return '-'
        return str(obj.ocr_content)

    ocr_content_formatted.short_description = _('OCR Content (Formatted)')

    def get_queryset(self, request):
        """
        Optimize queryset with select_related for user and email_message.
        """
        return super().get_queryset(request).select_related(
            'user', 'email_message'
        )


@admin.register(JiraIssue)
class JiraIssueAdmin(admin.ModelAdmin):
    """
    Admin interface for JIRA issues with issue tracking and URL management.
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
        Optimize queryset with select_related for user and email_message.
        """
        return super().get_queryset(request).select_related(
            'user', 'email_message'
        )
