from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from threadline.state_machine import (
    EmailStatus,
    get_initial_email_status,
    can_transition_to,
    get_next_states,
    EMAIL_STATE_MACHINE
)


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
        value_str = str(self.value)[:50]
        return f"{self.user.username} - {self.key}: {value_str}"

    @classmethod
    def get_user_config(
        cls,
        user,
        config_key: str,
        required_fields: list = None
    ):
        """
        Get user's configuration by key and validate required fields.

        This method provides a centralized way to access
        user configurations across tasks, views, and
        management commands.

        Args:
            user: User instance
            config_key: Configuration key
                (e.g., 'prompt_config', 'email_config')
            required_fields: List of required field keys to validate

        Returns:
            dict: Configuration value

        Raises:
            ValueError: If configuration is missing or incomplete
        """
        try:
            setting = cls.objects.get(
                user=user,
                key=config_key,
                is_active=True
            )
            config_value = setting.value

            # Validate required fields if specified
            if required_fields:
                missing_fields = [
                    field for field in required_fields
                    if not config_value.get(field)
                ]
                if missing_fields:
                    raise ValueError(
                        f"Missing fields in {config_key}: "
                        f"{', '.join(missing_fields)}"
                    )

            return config_value

        except cls.DoesNotExist:
            error_msg = (
                f"User {user.username} has no active "
                f"{config_key} setting"
            )
            raise ValueError(error_msg)

    @classmethod
    def get_user_prompt_config(
        cls,
        user,
        required_prompts: list = None
    ) -> dict:
        """
        Get user's prompt configuration and validate required prompts.

        This is a convenience method for the commonly used
        prompt_config.

        Args:
            user: User instance
            required_prompts: List of required prompt keys to validate

        Returns:
            dict: Prompt configuration
        """
        return cls.get_user_config(
            user,
            'prompt_config',
            required_prompts
        )


class EmailTask(models.Model):
    """
    Task execution records for various background tasks
    """
    class TaskStatus(models.TextChoices):
        RUNNING = 'running', _('Running')
        COMPLETED = 'completed', _('Completed')
        FAILED = 'failed', _('Failed')
        CANCELLED = 'cancelled', _('Cancelled')

    class TaskType(models.TextChoices):
        IMAP_FETCH = 'IMAP_EMAIL_FETCH', _('IMAP Email Fetch')
        HARAKA_FETCH = 'HARAKA_EMAIL_FETCH', _('Haraka Email Fetch')
        HARAKA_CLEANUP = 'HARAKA_CLEANUP', _('Haraka Cleanup')
        TASK_CLEANUP = 'TASK_CLEANUP', _('EmailTask Cleanup')
        STUCK_EMAIL_RESET = 'STUCK_EMAIL_RESET', _('Stuck Email Reset')

    task_type = models.CharField(
        max_length=20,
        choices=TaskType.choices,
        verbose_name=_('Task Type'),
        help_text=_('Type of task being executed')
    )
    task_id = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Celery Task ID'),
        help_text=_('Celery task ID for tracking')
    )
    status = models.CharField(
        max_length=20,
        choices=TaskStatus.choices,
        default=TaskStatus.RUNNING,
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
    error_message = models.TextField(
        blank=True,
        verbose_name=_('Error Message')
    )
    details = models.JSONField(
        default=list,
        verbose_name=_('Execution Details'),
        help_text=_('Detailed execution log and status information')
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Task')
        verbose_name_plural = _('Tasks')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['task_type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f"EmailTask({self.id}): {self.task_type}-{self.status}"


class EmailMessage(models.Model):
    """
    Email message details
    """

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
    sender = models.CharField(
        max_length=500,
        verbose_name=_('Sender'),
        help_text=_('Sender email address (supports RFC 5322 format)')
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
        choices=[(status.value, status.name.replace('_', ' ').title())
                 for status in EmailStatus],
        default=get_initial_email_status(),
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

    def set_status(self, status: str, error_message: str = None) -> None:
        """
        Set email status and optionally error message.

        When transitioning to SUCCESS status, error_message is
        automatically cleared to ensure clean state.

        Args:
            status: New status value
            error_message: Optional error message to save
        """
        update_fields = ['status']
        self.status = status

        # Clear error_message when transitioning to SUCCESS
        if status == EmailStatus.SUCCESS.value:
            self.error_message = ''
            update_fields.append('error_message')
        elif error_message:
            self.error_message = error_message
            update_fields.append('error_message')

        self.save(update_fields=update_fields)

    def save(self, *args, **kwargs):
        """
        Override save to automatically validate status transitions
        """
        # Skip state machine validation if saving from Django Admin
        if hasattr(self, '_from_admin'):
            # Clear the flag and save without validation
            delattr(self, '_from_admin')
            super().save(*args, **kwargs)
            return

        # Check if this is an update and status has changed
        if self.pk:
            try:
                old_instance = EmailMessage.objects.get(pk=self.pk)
                status_changed = old_instance.status != self.status
                if status_changed and not can_transition_to(
                    old_instance.status,
                    self.status,
                    EMAIL_STATE_MACHINE
                ):
                    # Get valid next states using the state machine
                    valid_transitions = get_next_states(
                        old_instance.status,
                        EMAIL_STATE_MACHINE
                    )
                    transitions_str = ', '.join(valid_transitions)
                    error_msg = (
                        f"Invalid email status transition from "
                        f"{old_instance.status} to {self.status}. "
                        f"Valid transitions: {transitions_str}"
                    )
                    raise ValidationError(error_msg)
            except EmailMessage.DoesNotExist:
                # New object, no validation needed
                pass

        super().save(*args, **kwargs)


class EmailAttachment(models.Model):
    """
    Email attachments without status field.

    Status is now managed by the parent EmailMessage.status field
    for unified workflow control.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_('User'),
        related_name='attachments'
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
        help_text=_('Original filename of the attachment')
    )
    safe_filename = models.CharField(
        max_length=255,
        verbose_name=_('Safe Filename'),
        help_text=_('Sanitized filename for safe storage')
    )
    content_type = models.CharField(
        max_length=100,
        verbose_name=_('Content Type'),
        help_text=_('MIME type of the attachment')
    )
    file_size = models.IntegerField(
        verbose_name=_('File Size'),
        help_text=_('Size of the attachment in bytes')
    )
    file_path = models.CharField(
        max_length=500,
        verbose_name=_('File Path'),
        help_text=_('Path to the stored attachment file')
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
    # Content processed/organized by LLM for this attachment
    # such as post-processed OCR result
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


class Issue(models.Model):
    """
    Generic issue model for external system integration.
    Supports multiple engines like Jira, email, Slack, etc.
    """
    # User who owns the issue
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_('User'),
        related_name='issues'
    )
    # Related email message
    email_message = models.ForeignKey(
        EmailMessage,
        on_delete=models.CASCADE,
        verbose_name=_('Email Message'),
        related_name='issues'
    )
    # Issue title
    title = models.CharField(
        max_length=255,
        verbose_name=_('Issue Title'),
        help_text=_('Title of the issue')
    )
    # Issue description
    description = models.TextField(
        verbose_name=_('Issue Description'),
        help_text=_('Description of the issue')
    )

    # Issue priority
    priority = models.CharField(
        max_length=20,
        verbose_name=_('Issue Priority'),
        help_text=_('Priority level of the issue')
    )
    # Engine type (jira, email, slack, etc.)
    engine = models.CharField(
        max_length=50,
        verbose_name=_('Engine Type'),
        help_text=_('External system engine type')
    )
    # External system ID (e.g., Jira issue key)
    external_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_('External ID'),
        help_text=_('ID in external system')
    )
    # Direct URL to the issue in external system
    issue_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name=_('Issue URL'),
        help_text=_('Direct link to the issue in external system')
    )
    # Metadata for engine-specific configuration and data
    metadata = models.JSONField(
        default=dict,
        verbose_name=_('Metadata'),
        help_text=_('Engine-specific configuration and data')
    )
    # Created timestamp
    created_at = models.DateTimeField(auto_now_add=True)
    # Updated timestamp
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Issue')
        verbose_name_plural = _('Issues')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'email_message']),
            models.Index(fields=['engine']),
            models.Index(fields=['external_id']),
        ]

    def __str__(self):
        return f"{self.title} ({self.engine})"

    def save(self, *args, **kwargs):
        """
        Override save for any custom logic if needed
        """
        super().save(*args, **kwargs)


class EmailAlias(models.Model):
    """
    Email alias management for auto-assign mode users

    Allows users to create additional email aliases that route to
    their account. All aliases must be unique across the system to
    prevent conflicts.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_('User'),
        related_name='email_aliases',
        help_text=_('User who owns this email alias')
    )
    alias = models.CharField(
        max_length=255,
        verbose_name=_('Alias'),
        help_text=_('Email alias name (domain is auto-assigned)')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Active'),
        help_text=_('Whether this alias is active')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated At')
    )

    class Meta:
        verbose_name = _('Email Alias')
        verbose_name_plural = _('Email Aliases')
        unique_together = ['alias']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['alias']),
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        email_addr = (
            f"{self.alias}@{settings.AUTO_ASSIGN_EMAIL_DOMAIN}"
        )
        return f"{email_addr} -> {self.user.username}"

    def full_email_address(self):
        """Return full email address"""
        return f"{self.alias}@{settings.AUTO_ASSIGN_EMAIL_DOMAIN}"

    @classmethod
    def is_unique(cls, alias):
        """Check if alias is unique across the system"""
        return not cls.objects.filter(alias=alias).exists()

    @classmethod
    def find_user_by_email(cls, email_address):
        """Find user by email address (supports aliases)"""
        try:
            alias_name, domain = email_address.split('@')
            if domain != settings.AUTO_ASSIGN_EMAIL_DOMAIN:
                return None
            alias_obj = cls.objects.get(
                alias=alias_name,
                is_active=True
            )
            return alias_obj.user
        except (cls.DoesNotExist, ValueError):
            return None

    @classmethod
    def get_user_aliases(cls, user, active_only=True):
        """Get all aliases for a user"""
        queryset = cls.objects.filter(user=user)
        if active_only:
            queryset = queryset.filter(is_active=True)
        return queryset.order_by('alias')
