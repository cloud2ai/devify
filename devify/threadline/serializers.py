from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

from .models import (
    Settings,
    EmailTask,
    EmailMessage,
    EmailAttachment,
    Issue
)


class UserSerializer(serializers.ModelSerializer):
    """
    User serializer for nested serialization
    """

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id', 'username']


class SettingsSerializer(serializers.ModelSerializer):
    """
    Main serializer for Settings model - used for display
    """

    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Settings
        fields = [
            'id', 'user', 'user_id', 'key', 'value', 'description',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_key(self, value):
        """
        Validate setting key format
        """
        if not value or not value.strip():
            raise serializers.ValidationError(
                _("Setting key cannot be empty")
            )

        # Check for valid key format (alphanumeric, underscore, dot)
        import re
        if not re.match(r'^[a-zA-Z0-9_.-]+$', value):
            raise serializers.ValidationError(
                _("Setting key can only contain letters, numbers, "
                  "underscores, dots, and hyphens")
            )

        return value.strip()

    def validate_user_id(self, value):
        """
        Validate user exists and user can access it
        """
        try:
            user = User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                _("User with this ID does not exist")
            )

        # Check if user can access this setting
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            if request.user != user and not request.user.is_superuser:
                raise serializers.ValidationError(
                    _("You can only create settings for yourself")
                )

        return value

    def validate_key(self, value):
        """
        Validate key format
        """
        import re
        # Key should only contain alphanumeric characters, underscores, and hyphens
        if not re.match(r'^[a-zA-Z0-9_-]+$', value):
            raise serializers.ValidationError(
                _("Key can only contain letters, numbers, underscores, and hyphens")
            )
        return value

    def validate(self, attrs):
        """
        Object-level validation
        """
        user_id = attrs.get('user_id')
        key = attrs.get('key')

        if user_id and key:
            # Check for duplicate key for the same user
            queryset = Settings.objects.filter(user_id=user_id, key=key)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)

            if queryset.exists():
                raise serializers.ValidationError(
                    _("A setting with this key already exists for this user")
                )

        return attrs


class SettingsCreateSerializer(serializers.ModelSerializer):
    """
    Create serializer for Settings model
    """

    class Meta:
        model = Settings
        fields = ['user_id', 'key', 'value', 'description', 'is_active']

    def validate_user_id(self, value):
        """
        Validate user exists and set from request context
        """
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            # Auto-set user from request
            return request.user.id

        try:
            user = User.objects.get(id=value)
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError(
                _("User with this ID does not exist")
            )

    def validate_key(self, value):
        """
        Validate key format
        """
        import re
        # Key should only contain alphanumeric characters, underscores, and hyphens
        if not re.match(r'^[a-zA-Z0-9_-]+$', value):
            raise serializers.ValidationError(
                _("Key can only contain letters, numbers, underscores, and hyphens")
            )
        return value

    def create(self, validated_data):
        """
        Create a new setting instance
        """
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            # Set user from request context
            validated_data['user'] = request.user
        else:
            # Set user from user_id
            user_id = validated_data.pop('user_id', None)
            if user_id:
                validated_data['user'] = User.objects.get(id=user_id)

        return super().create(validated_data)


class SettingsUpdateSerializer(serializers.ModelSerializer):
    """
    Update serializer for Settings model
    """

    class Meta:
        model = Settings
        fields = ['value', 'description', 'is_active']


class EmailTaskSerializer(serializers.ModelSerializer):
    """
    Main serializer for EmailTask model - used for display
    """

    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = EmailTask
        fields = [
            'id', 'user', 'user_id', 'status', 'status_display',
            'emails_processed', 'emails_created_issues',
            'started_at', 'completed_at', 'error_message',
            'created_at'
        ]
        read_only_fields = [
            'id', 'status', 'emails_processed', 'emails_created_issues',
            'started_at', 'completed_at', 'created_at'
        ]

    def validate_user_id(self, value):
        """
        Validate user exists and user can access it
        """
        try:
            user = User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                _("User with this ID does not exist")
            )

        # Check if user can access this task
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            if request.user != user and not request.user.is_superuser:
                raise serializers.ValidationError(
                    _("You can only create tasks for yourself")
                )

        return value


class EmailTaskCreateSerializer(serializers.ModelSerializer):
    """
    Create serializer for EmailTask model
    """

    class Meta:
        model = EmailTask
        fields = ['user_id']

    def validate_user_id(self, value):
        """
        Validate user exists and set from request context
        """
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            # Auto-set user from request
            return request.user.id

        try:
            user = User.objects.get(id=value)
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError(
                _("User with this ID does not exist")
            )


class EmailTaskUpdateSerializer(serializers.ModelSerializer):
    """
    Update serializer for EmailTask model
    """

    class Meta:
        model = EmailTask
        fields = ['status', 'error_message']


class EmailAttachmentNestedSerializer(serializers.ModelSerializer):
    """
    Nested serializer for EmailAttachment - used within EmailMessage
    """

    class Meta:
        model = EmailAttachment
        fields = [
            'id', 'filename', 'content_type', 'file_size', 'file_path',
            'ocr_content', 'llm_content', 'is_image', 'safe_filename',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class EmailMessageSerializer(serializers.ModelSerializer):
    """
    Main serializer for EmailMessage model - used for display
    """

    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)
    task = EmailTaskSerializer(read_only=True)
    task_id = serializers.IntegerField(write_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    attachments = serializers.SerializerMethodField()

    class Meta:
        model = EmailMessage
        fields = [
            'id', 'user', 'user_id', 'task', 'task_id', 'message_id',
            'subject', 'sender', 'recipients', 'received_at',
            'raw_content', 'html_content', 'text_content',
            'summary_title', 'summary_content', 'summary_priority',
            'llm_content', 'status', 'status_display', 'error_message',
            'attachments', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'status', 'created_at', 'updated_at'
        ]

    def get_attachments(self, obj) -> list:
        """
        Get attachments for this email message

        Returns:
            list: List of attachment data dictionaries
        """
        attachments = obj.attachments.all()
        return EmailAttachmentNestedSerializer(attachments, many=True, context=self.context).data

    def validate_user_id(self, value):
        """
        Validate user exists and user can access it
        """
        try:
            user = User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                _("User with this ID does not exist")
            )

        # Check if user can access this message
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            if request.user != user and not request.user.is_superuser:
                raise serializers.ValidationError(
                    _("You can only create messages for yourself")
                )

        return value

    def validate_task_id(self, value):
        """
        Validate task exists and belongs to the user
        """
        try:
            task = EmailTask.objects.get(id=value)
        except EmailTask.DoesNotExist:
            raise serializers.ValidationError(
                _("Email task with this ID does not exist")
            )

        # Check if task belongs to the user
        user_id = self.initial_data.get('user_id')
        if user_id and task.user_id != user_id:
            raise serializers.ValidationError(
                _("Email task does not belong to the specified user")
            )

        return value

    def validate_message_id(self, value):
        """
        Validate message ID format and uniqueness
        """
        if not value or not value.strip():
            raise serializers.ValidationError(
                _("Message ID cannot be empty")
            )

        user_id = self.initial_data.get('user_id')
        if user_id:
            # Check for duplicate message ID for the same user
            queryset = EmailMessage.objects.filter(user_id=user_id, message_id=value)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)

            if queryset.exists():
                raise serializers.ValidationError(
                    _("A message with this ID already exists for this user")
                )

        return value.strip()

    def validate_status(self, value):
        """
        Validate status transition
        """
        if self.instance and self.instance.status != value:
            from .state_machine import can_transition_to, EMAIL_STATE_MACHINE

            if not can_transition_to(self.instance.status, value, EMAIL_STATE_MACHINE):
                raise serializers.ValidationError(
                    _("Invalid status transition from {} to {}").format(
                        self.instance.status, value
                    )
                )

        return value


class EmailMessageCreateSerializer(serializers.ModelSerializer):
    """
    Create serializer for EmailMessage model
    """

    class Meta:
        model = EmailMessage
        fields = [
            'user_id', 'task_id', 'message_id', 'subject', 'sender',
            'recipients', 'received_at', 'raw_content', 'html_content',
            'text_content'
        ]

    def validate_user_id(self, value):
        """
        Validate user exists and set from request context
        """
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            # Auto-set user from request
            return request.user.id

        if value is None:
            raise serializers.ValidationError(
                _("User ID is required")
            )

        try:
            user = User.objects.get(id=value)
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError(
                _("User with this ID does not exist")
            )

    def validate_task_id(self, value):
        """
        Validate task exists and belongs to the user
        """
        if value is None:
            raise serializers.ValidationError(
                _("Task ID is required")
            )

        try:
            task = EmailTask.objects.get(id=value)
        except EmailTask.DoesNotExist:
            raise serializers.ValidationError(
                _("Email task with this ID does not exist")
            )

        # Check if task belongs to the user
        # Get user_id from validated data or initial data
        user_id = self.initial_data.get('user_id')
        if not user_id:
            # Try to get from request context
            request = self.context.get('request')
            if request and hasattr(request, 'user'):
                user_id = request.user.id

        if user_id and task.user_id != user_id:
            raise serializers.ValidationError(
                _("Email task does not belong to the specified user")
            )

        return value

    def create(self, validated_data):
        """
        Create a new email message instance
        """
        # Ensure user_id is set from request context if not provided
        request = self.context.get('request')
        if request and hasattr(request, 'user') and 'user_id' not in validated_data:
            validated_data['user_id'] = request.user.id

        # Ensure task_id is properly set
        if 'task_id' not in validated_data or validated_data['task_id'] is None:
            raise serializers.ValidationError(
                _("Task ID is required")
            )

        return super().create(validated_data)


class EmailMessageUpdateSerializer(serializers.ModelSerializer):
    """
    Update serializer for EmailMessage model
    """

    class Meta:
        model = EmailMessage
        fields = [
            'subject', 'sender', 'recipients', 'raw_content',
            'html_content', 'text_content', 'summary_title',
            'summary_content', 'summary_priority', 'llm_content',
            'status', 'error_message'
        ]


class EmailAttachmentSerializer(serializers.ModelSerializer):
    """
    Main serializer for EmailAttachment model - used for display
    """

    email_message = EmailMessageSerializer(read_only=True)
    email_message_id = serializers.IntegerField(write_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = EmailAttachment
        fields = [
            'id', 'email_message', 'email_message_id', 'filename',
            'content_type', 'file_size', 'file_path', 'content',
            'llm_content', 'status', 'status_display', 'error_message',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'status', 'created_at', 'updated_at'
        ]


    def validate_email_message_id(self, value):
        """
        Validate email message exists
        """
        try:
            email_message = EmailMessage.objects.get(id=value)
        except EmailMessage.DoesNotExist:
            raise serializers.ValidationError(
                _("Email message with this ID does not exist")
            )

        return value

    def validate_status(self, value):
        """
        Validate status transition
        """
        if self.instance and self.instance.status != value:
            from .state_machine import can_transition_to, EMAIL_STATE_MACHINE

            if not can_transition_to(self.instance.status, value, EMAIL_STATE_MACHINE):
                raise serializers.ValidationError(
                    _("Invalid status transition from {} to {}").format(
                        self.instance.status, value
                    )
                )

        return value


class EmailAttachmentCreateSerializer(serializers.ModelSerializer):
    """
    Create serializer for EmailAttachment model
    """

    class Meta:
        model = EmailAttachment
        fields = [
            'email_message_id', 'filename', 'content_type',
            'file_size', 'file_path', 'content'
        ]


class EmailAttachmentUpdateSerializer(serializers.ModelSerializer):
    """
    Update serializer for EmailAttachment model
    """

    class Meta:
        model = EmailAttachment
        fields = [
            'filename', 'content_type', 'file_size', 'file_path',
            'content', 'llm_content', 'status', 'error_message'
        ]


class IssueSerializer(serializers.ModelSerializer):
    """
    Main serializer for Issue model - used for display
    """

    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)
    email_message = EmailMessageSerializer(read_only=True)
    email_message_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Issue
        fields = [
            'id', 'user', 'user_id', 'email_message', 'email_message_id',
            'title', 'description', 'priority', 'engine', 'external_id',
            'issue_url', 'metadata', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_user_id(self, value):
        """
        Validate user exists and user can access it
        """
        try:
            user = User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                _("User with this ID does not exist")
            )

        # Check if user can access this issue
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            if request.user != user and not request.user.is_superuser:
                raise serializers.ValidationError(
                    _("You can only create issues for yourself")
                )

        return value

    def validate_email_message_id(self, value):
        """
        Validate email message exists and belongs to the user
        """
        try:
            email_message = EmailMessage.objects.get(id=value)
        except EmailMessage.DoesNotExist:
            raise serializers.ValidationError(
                _("Email message with this ID does not exist")
            )

        # Check if email message belongs to the user
        user_id = self.initial_data.get('user_id')
        if user_id and email_message.user_id != user_id:
            raise serializers.ValidationError(
                _("Email message does not belong to the specified user")
            )

        return value

    def validate_engine(self, value):
        """
        Validate engine type
        """
        valid_engines = ['jira', 'email', 'slack', 'github', 'gitlab', 'trello']
        if value.lower() not in valid_engines:
            raise serializers.ValidationError(
                _("Engine must be one of: {}").format(', '.join(valid_engines))
            )

        return value.lower()

    def validate_priority(self, value):
        """
        Validate priority level
        """
        valid_priorities = ['low', 'medium', 'high', 'critical', 'urgent']
        if value.lower() not in valid_priorities:
            raise serializers.ValidationError(
                _("Priority must be one of: {}").format(', '.join(valid_priorities))
            )

        return value.lower()


class IssueCreateSerializer(serializers.ModelSerializer):
    """
    Create serializer for Issue model
    """

    class Meta:
        model = Issue
        fields = [
            'user_id', 'email_message_id', 'title', 'description',
            'priority', 'engine', 'external_id', 'issue_url', 'metadata'
        ]

    def validate_user_id(self, value):
        """
        Validate user exists and set from request context
        """
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            # Auto-set user from request
            return request.user.id

        try:
            user = User.objects.get(id=value)
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError(
                _("User with this ID does not exist")
            )


class IssueUpdateSerializer(serializers.ModelSerializer):
    """
    Update serializer for Issue model
    """

    class Meta:
        model = Issue
        fields = [
            'title', 'description', 'priority', 'engine',
            'external_id', 'issue_url', 'metadata'
        ]