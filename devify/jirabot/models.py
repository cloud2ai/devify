from django.db import models
from django.contrib.auth.models import User
from django.core.validators import URLValidator
from django.utils.translation import gettext_lazy as _


class Settings(models.Model):
    """
    User settings using key-value design with JSON values
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_('User'),
        related_name='settings'
    )
    key = models.CharField(
        max_length=100,
        verbose_name=_('Setting Key'),
        help_text=_('Configuration key name')
    )
    value = models.JSONField(
        verbose_name=_('Setting Value'),
        help_text=_('Configuration value (JSON format)')
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Description'),
        help_text=_('Description of this setting')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Active'),
        help_text=_('Whether this setting is active')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Setting')
        verbose_name_plural = _('Settings')
        ordering = ['user', 'key']
        unique_together = ['user', 'key']
        indexes = [
            models.Index(fields=['user', 'key']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.key}: {str(self.value)[:50]}"


class EmailTask(models.Model):
    """
    Email scanning task execution records
    """
    class TaskStatus(models.TextChoices):
        PENDING = 'pending', _('Pending')
        RUNNING = 'running', _('Running')
        COMPLETED = 'completed', _('Completed')
        FAILED = 'failed', _('Failed')
        CANCELLED = 'cancelled', _('Cancelled')

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_('User'),
        related_name='email_tasks'
    )
    status = models.CharField(
        max_length=20,
        choices=TaskStatus.choices,
        default=TaskStatus.PENDING,
        verbose_name=_('Task Status')
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Started At')
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Completed At')
    )
    emails_processed = models.IntegerField(
        default=0,
        verbose_name=_('Emails Processed')
    )
    emails_created_issues = models.IntegerField(
        default=0,
        verbose_name=_('Issues Created')
    )
    error_message = models.TextField(
        blank=True,
        verbose_name=_('Error Message')
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Email Task')
        verbose_name_plural = _('Email Tasks')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Task {self.id} - {self.user.username} - {self.status}"


class EmailMessage(models.Model):
    """
    Email message details
    """
    class ProcessingStatus(models.TextChoices):
        PENDING = 'pending', _('Pending')
        FETCHED = 'fetched', _('Fetched')
        OCR_PROCESSING = 'ocr_processing', _('OCR Processing')
        OCR_FAILED = 'ocr_failed', _('OCR Failed')
        OCR_SUCCESS = 'ocr_success', _('OCR Success')
        SUMMARY_PROCESSING = 'summary_processing', _('Summary Processing')
        SUMMARY_FAILED = 'summary_failed', _('Summary Failed')
        SUMMARY_SUCCESS = 'summary_success', _('Summary Success')
        JIRA_PROCESSING = 'jira_processing', _('JIRA Processing')
        JIRA_FAILED = 'jira_failed', _('JIRA Failed')
        JIRA_SUCCESS = 'jira_success', _('JIRA Success')
        ATTACHMENT_UPLOADING = (
            'attachment_uploading',
            _('Attachment Uploading')
        )
        ATTACHMENT_UPLOAD_FAILED = (
            'attachment_upload_failed',
            _('Attachment Upload Failed')
        )
        ATTACHMENT_UPLOADED = (
            'attachment_uploaded',
            _('Attachment Uploaded')
        )
        SUCCESS = 'success', _('Success')
        FAILED = 'failed', _('Failed')
        SKIPPED = 'skipped', _('Skipped')

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_('User'),
        related_name='email_messages'
    )
    task = models.ForeignKey(
        EmailTask,
        on_delete=models.CASCADE,
        verbose_name=_('Email Task'),
        related_name='email_messages'
    )
    message_id = models.CharField(
        max_length=255,
        verbose_name=_('Message ID'),
        help_text=_('Unique email message ID')
    )
    subject = models.CharField(
        max_length=500,
        verbose_name=_('Subject')
    )
    sender = models.EmailField(
        verbose_name=_('Sender')
    )
    recipients = models.TextField(
        verbose_name=_('Recipients'),
        help_text=_('Comma-separated list of recipients')
    )
    received_at = models.DateTimeField(
        verbose_name=_('Received At')
    )
    raw_content = models.TextField(
        verbose_name=_('Raw Content'),
        help_text=_('Original email content')
    )
    html_content = models.TextField(
        blank=True,
        verbose_name=_('HTML Content')
    )
    text_content = models.TextField(
        blank=True,
        verbose_name=_('Text Content')
    )

    # Summarization results
    summary_title = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_('Summary Title')
    )
    summary_content = models.TextField(
        blank=True,
        verbose_name=_('Summary Content')
    )
    summary_priority = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_('Summary Priority')
    )

    # LLM processed/organized content for this email
    llm_content = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('LLM Processed Content'),
        help_text=_('Content organized by large language model')
    )

    # Processing status for each stage of the email workflow
    status = models.CharField(
        max_length=32,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDING,
        db_index=True,
        verbose_name=_('Processing Status')
    )
    error_message = models.TextField(
        blank=True,
        verbose_name=_('Error Message')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Email Message')
        verbose_name_plural = _('Email Messages')
        ordering = ['-received_at']
        indexes = [
            models.Index(fields=['user', 'message_id']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['received_at']),
        ]
        unique_together = ['user', 'message_id']

    def __str__(self):
        return f"{self.subject} - {self.sender}"


class EmailAttachment(models.Model):
    """
    Email attachments
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_('User'),
        related_name='email_attachments'
    )
    email_message = models.ForeignKey(
        EmailMessage,
        on_delete=models.CASCADE,
        verbose_name=_('Email Message'),
        related_name='attachments'
    )
    filename = models.CharField(
        max_length=255,
        verbose_name=_('Filename'),
        help_text=_('Original filename from email')
    )
    safe_filename = models.CharField(
        max_length=255,
        verbose_name=_('Safe Filename'),
        help_text=_('UUID-based filename for file system storage'),
        null=True,
        blank=True
    )
    content_type = models.CharField(
        max_length=100,
        verbose_name=_('Content Type')
    )
    file_size = models.IntegerField(
        verbose_name=_('File Size (bytes)')
    )
    file_path = models.CharField(
        max_length=500,
        verbose_name=_('File Path'),
        help_text=_('Path to stored file')
    )
    is_image = models.BooleanField(
        default=False,
        verbose_name=_('Is Image'),
        help_text=_('Whether this attachment is an image')
    )
    ocr_content = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('OCR Content'),
        help_text=_('Text content recognized from image attachment')
    )
    """
    Content processed/organized by LLM for this attachment,
    such as post-processed OCR result.
    """
    llm_content = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('LLM Processed Content'),
        help_text=_(
            'Content organized by large language model '
            'based on OCR result'
        )
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Email Attachment')
        verbose_name_plural = _('Email Attachments')
        ordering = ['filename']
        indexes = [
            models.Index(fields=['user', 'is_image']),
            models.Index(fields=['email_message']),
        ]

    def __str__(self):
        return f"{self.filename} ({self.content_type})"


class JiraIssue(models.Model):
    """
    Mapping between email messages and JIRA issues.
    """
    # User who owns the JIRA issue
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_('User'),
        related_name='jira_issues'
    )
    # Related email message (one email can have multiple JIRA issues)
    email_message = models.ForeignKey(
        EmailMessage,
        on_delete=models.CASCADE,
        verbose_name=_('Email Message'),
        related_name='jira_issues'
    )
    # JIRA issue key (e.g., PROJ-123)
    jira_issue_key = models.CharField(
        max_length=50,
        verbose_name=_('JIRA Issue Key'),
        help_text=_('JIRA issue key (e.g., PROJ-123)')
    )
    # JIRA issue URL
    jira_url = models.URLField(
        verbose_name=_('JIRA Issue URL')
    )
    # Created timestamp
    created_at = models.DateTimeField(auto_now_add=True)
    # Updated timestamp
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('JIRA Issue')
        verbose_name_plural = _('JIRA Issues')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'email_message']),
            models.Index(fields=['jira_issue_key']),
        ]

    def __str__(self):
        return f"{self.jira_issue_key} ({self.email_message})"
