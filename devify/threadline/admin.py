import json

from django import forms
from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django_json_widget.widgets import JSONEditorWidget
from django.utils import timezone


def format_content_for_admin(content, max_length=1000):
    """
    Generic function to format content for admin display with truncation.

    Args:
        content: The content to format (can be string, dict, list, or other)
        max_length: Maximum length before truncation (default: 1000)

    Returns:
        str: Formatted content, truncated if necessary
    """
    if not content:
        return '-'

    try:
        # Try to parse as JSON if it's a string
        if isinstance(content, str):
            try:
                parsed_content = json.loads(content)
                formatted_content = json.dumps(
                    parsed_content, indent=2, ensure_ascii=False
                )
            except json.JSONDecodeError:
                formatted_content = content
        else:
            # If already a dict/list, format as JSON
            formatted_content = json.dumps(content, indent=2, ensure_ascii=False)

        # Truncate if too long
        if len(formatted_content) > max_length:
            truncated = (
                formatted_content[:max_length] +
                '...\n\n[Content truncated for display. '
                'Full content available in database.]'
            )
            return truncated

        return formatted_content

    except (TypeError, ValueError):
        # Fallback to string representation
        text_content = str(content)

        if len(text_content) > max_length:
            truncated = (
                text_content[:max_length] +
                '...\n\n[Content truncated for display. '
                'Full content available in database.]'
            )
            return truncated

        return text_content

from .models import (
    Settings,
    EmailTask,
    EmailMessage,
    EmailAttachment,
    Issue
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
        Returns JSON string to ensure JavaScript compatibility.
        """
        if value is None:
            return ''
        if isinstance(value, (dict, list)):
            # Convert Python object to JSON string for JavaScript compatibility
            return json.dumps(value, indent=2, ensure_ascii=False)
        if isinstance(value, str):
            try:
                # Try to parse and reformat as JSON string
                parsed = json.loads(value)
                return json.dumps(parsed, indent=2, ensure_ascii=False)
            except json.JSONDecodeError:
                return value
        return value


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


class IssueAdminForm(forms.ModelForm):
    """
    Custom admin form for Issue, using SafeJSONEditorWidget for
    metadata field.
    """

    class Meta:
        model = Issue
        fields = '__all__'
        widgets = {
            'metadata': SafeJSONEditorWidget
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

    actions = ['reset_to_fetched']

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
        return format_content_for_admin(obj.ocr_content)

    ocr_content_formatted.short_description = _('OCR Content (Formatted)')

    def llm_content_formatted(self, obj):
        """
        Format LLM content for better display with JSON formatting.
        Truncate long content to improve admin readability.
        """
        if not obj.llm_content:
            return '-'

        try:
            # Try to parse as JSON
            if isinstance(obj.llm_content, str):
                content = json.loads(obj.llm_content)
            else:
                content = obj.llm_content

            formatted_content = json.dumps(
                content,
                indent=2,
                ensure_ascii=False
            )

            # Truncate content if too long (max 1000 characters)
            if len(formatted_content) > 1000:
                truncated = (
                    formatted_content[:1000] +
                    '...\n\n[Content truncated for display. '
                    'Full content available in database.]'
                )
                return truncated

            return formatted_content
        except (json.JSONDecodeError, TypeError):
            # If not JSON, display as formatted text
            text_content = str(obj.llm_content)

            # Truncate content if too long (max 1000 characters)
            if len(text_content) > 1000:
                truncated = (
                    text_content[:1000] +
                    '...\n\n[Content truncated for display. '
                    'Full content available in database.]'
                )
                return truncated

            return text_content

    llm_content_formatted.short_description = _('LLM Content (Formatted)')

    def raw_content_formatted(self, obj):
        """
        Format raw content for better display with JSON formatting.
        Truncate long content to improve admin readability.
        """
        if not obj.raw_content:
            return '-'

        try:
            # Try to parse as JSON
            if isinstance(obj.raw_content, str):
                content = json.loads(obj.raw_content)
            else:
                content = obj.raw_content

            formatted_content = json.dumps(
                content,
                indent=2,
                ensure_ascii=False
            )

            # Truncate content if too long (max 500 characters for admin)
            if len(formatted_content) > 500:
                truncated = (
                    formatted_content[:500] +
                    '...\n\n[Content truncated for display. '
                    'Full content available in database.]'
                )
                return truncated

            return formatted_content
        except (json.JSONDecodeError, TypeError):
            # If not JSON, display as formatted text
            text_content = str(obj.raw_content)

            # Truncate text content if too long (max 500 characters for admin)
            if len(text_content) > 500:
                truncated = (
                    text_content[:500] +
                    '...\n\n[Content truncated for display. '
                    'Full content available in database.]'
                )
                return truncated

            return text_content

    raw_content_formatted.short_description = _('Raw Content (Formatted)')

    def get_queryset(self, request):
        """
        Optimize queryset with select_related for user and task.
        """
        return super().get_queryset(request).select_related('user', 'task')

    def reset_to_fetched(self, request, queryset):
        """
        Reset selected emails to FETCHED status for reprocessing.
        This bypasses state machine validation for admin convenience.
        """
        from threadline.state_machine import EmailStatus

        count = 0
        for email in queryset:
            if email.status != EmailStatus.FETCHED.value:
                # Set admin flag to bypass validation
                email._from_admin = True
                email.status = EmailStatus.FETCHED.value
                email.error_message = ''  # Clear any error messages
                email.save()
                count += 1

        if count == 1:
            message = f"1 email has been reset to FETCHED status."
        else:
            message = f"{count} emails have been reset to FETCHED status."

        self.message_user(request, message)

    reset_to_fetched.short_description = (
        "Reset selected emails to FETCHED status"
    )
    reset_to_fetched.help_text = (
        "Force reset email status to FETCHED for reprocessing"
    )

    def save_model(self, request, obj, form, change):
        """
        Override save_model to handle status changes from admin interface.
        This bypasses state machine validation for admin convenience.
        """
        if change:  # Only for updates, not new objects
            # Set admin flag to bypass validation
            obj._from_admin = True

        super().save_model(request, obj, form, change)


@admin.register(EmailAttachment)
class EmailAttachmentAdmin(admin.ModelAdmin):
    """
    Admin interface for email attachments with content formatting and
    file management.
    """

    form = EmailAttachmentAdminForm
    list_display = [
        'filename', 'safe_filename', 'user', 'email_message', 'content_type',
        'file_size', 'is_image', 'created_at'
    ]
    list_filter = ['is_image', 'content_type', 'created_at']
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

    def save_model(self, request, obj, form, change):
        """
        Override save_model to handle attachment updates from Django Admin.
        """
        super().save_model(request, obj, form, change)

    def llm_content_formatted(self, obj):
        """
        Format LLM content for better display with JSON formatting.
        Truncate long content to improve admin readability.
        """
        if not obj.llm_content:
            return '-'

        try:
            # Try to parse as JSON
            if isinstance(obj.llm_content, str):
                content = json.loads(obj.llm_content)
            else:
                content = obj.llm_content

            formatted_content = json.dumps(
                content, indent=2, ensure_ascii=False
            )

            # Truncate content if too long (max 1000 characters)
            if len(formatted_content) > 1000:
                truncated = (
                    formatted_content[:1000] +
                    '...\n\n[Content truncated for display. '
                    'Full content available in database.]'
                )
                return truncated

            return formatted_content
        except (json.JSONDecodeError, TypeError):
            # If not JSON, display as formatted text
            text_content = str(obj.llm_content)

            # Truncate content if too long (max 1000 characters)
            if len(text_content) > 1000:
                truncated = (
                    text_content[:1000] +
                    '...\n\n[Content truncated for display. '
                    'Full content available in database.]'
                )
                return truncated

            return text_content

    llm_content_formatted.short_description = _('LLM Content (Formatted)')

    def ocr_content_formatted(self, obj):
        """
        Format OCR content for better display.
        Truncate long content to improve admin readability.
        """
        if not obj.ocr_content:
            return '-'

        text_content = str(obj.ocr_content)

        # Truncate content if too long (max 1000 characters)
        if len(text_content) > 1000:
            truncated = (
                text_content[:1000] +
                '...\n\n[Content truncated for display. '
                'Full content available in database.]'
            )
            return truncated

        return text_content

    ocr_content_formatted.short_description = _('OCR Content (Formatted)')

    def get_queryset(self, request):
        """
        Optimize queryset with select_related for user and email_message.
        """
        return super().get_queryset(request).select_related(
            'user', 'email_message'
        )

    def save_model(self, request, obj, form, change):
        """
        Override save_model to handle status changes from admin interface.
        This bypasses state machine validation for admin convenience.
        """
        if change:  # Only for updates, not new objects
            # Set admin flag to bypass validation
            obj._from_admin = True

        super().save_model(request, obj, form, change)


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    """
    Admin interface for generic issues with engine abstraction.
    """

    form = IssueAdminForm
    list_display = [
        'title', 'engine', 'priority', 'user',
        'email_message', 'external_id', 'issue_url', 'created_at'
    ]
    list_filter = ['engine', 'priority', 'created_at']
    search_fields = [
        'title', 'description', 'external_id',
        'email_message__subject', 'user__username'
    ]
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        (_('Issue Information'), {
            'fields': (
                'title', 'description', 'priority'
            )
        }),
        (_('Engine Configuration'), {
            'fields': ('engine', 'external_id', 'issue_url', 'metadata'),
            'classes': ('collapse',)
        }),
        (_('Relationships'), {
            'fields': ('user', 'email_message'),
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
