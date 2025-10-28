import re

from django.conf import settings
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .models import (
    Settings,
    EmailTask,
    EmailMessage,
    EmailAttachment,
    EmailAlias,
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

    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    task_type_display = serializers.CharField(
        source='get_task_type_display',
        read_only=True
    )

    class Meta:
        model = EmailTask
        fields = [
            'id', 'task_type', 'task_type_display', 'status',
            'status_display', 'started_at', 'completed_at',
            'error_message', 'details', 'task_id', 'created_at'
        ]
        read_only_fields = [
            'id', 'status', 'started_at', 'completed_at', 'created_at'
        ]


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
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    attachments = serializers.SerializerMethodField()

    class Meta:
        model = EmailMessage
        fields = [
            'id', 'uuid', 'user', 'user_id', 'message_id',
            'subject', 'sender', 'recipients', 'received_at',
            'raw_content', 'html_content', 'text_content',
            'summary_title', 'summary_content', 'summary_priority',
            'llm_content', 'metadata', 'status', 'status_display',
            'error_message', 'attachments', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'uuid', 'status', 'created_at', 'updated_at'
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

    def _replace_image_placeholders_with_urls(
        self,
        content: str,
        attachment_url_map: dict
    ) -> str:
        """
        Replace image placeholders with Markdown image syntax.

        Args:
            content: Content with [IMAGE: filename] placeholders
            attachment_url_map: Dict mapping safe_filename to URL

        Returns:
            str: Content with placeholders replaced by ![](url)
        """
        if not content:
            return content

        pattern = r'\[IMAGE:\s*([^\]]+)\]'

        def replacer(match):
            filename = match.group(1).strip()
            url = attachment_url_map.get(filename, '')
            return f"![]({url})" if url else match.group(0)

        return re.sub(pattern, replacer, content)

    def to_representation(self, instance):
        """
        Convert instance to representation with image placeholders replaced.

        Dynamically generates URLs from attachment file_path for automatic
        backward compatibility with both old (email_id) and new (uuid) paths.

        Args:
            instance: EmailMessage instance

        Returns:
            dict: Serialized data with replaced image placeholders
        """
        data = super().to_representation(instance)

        # Check if this is a list view by checking if parent serializer has many=True
        is_list_view = self.parent is not None

        # Only limit content for list views to reduce payload size
        # Detail views should return full content
        if is_list_view:
            # Remove large content fields to reduce payload size
            data.pop('raw_content', None)
            data.pop('html_content', None)

            # Limit text_content and llm_content for preview
            max_length = 500
            if data.get('text_content'):
                if len(data['text_content']) > max_length:
                    text_content = data['text_content'][:max_length] + '...'
                    data['text_content'] = text_content

            if data.get('llm_content'):
                if len(data['llm_content']) > max_length:
                    llm_content = data['llm_content'][:max_length] + '...'
                    data['llm_content'] = llm_content

        # Build filename to URL mapping from attachments
        attachment_url_map = {}
        for att in instance.attachments.all():
            if att.is_image and att.file_path:
                # Extract relative path from file_path
                # Supports both: email_217/file.jpg and uuid/file.jpg
                rel_path = att.file_path.replace(
                    settings.EMAIL_ATTACHMENT_DIR + '/',
                    ''
                ).lstrip('/')

                # Generate URL
                if settings.ATTACHMENT_BASE_URL:
                    url = f"{settings.ATTACHMENT_BASE_URL}/attachments/{rel_path}"
                else:
                    url = f"/attachments/{rel_path}"

                attachment_url_map[att.safe_filename] = url

        # Replace placeholders in all content fields
        for field in ['llm_content', 'summary_content']:
            if data.get(field):
                data[field] = self._replace_image_placeholders_with_urls(
                    data[field],
                    attachment_url_map
                )

        return data


class EmailMessageCreateSerializer(serializers.ModelSerializer):
    """
    Create serializer for EmailMessage model
    """

    class Meta:
        model = EmailMessage
        fields = [
            'user_id', 'message_id', 'subject', 'sender',
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

    def create(self, validated_data):
        """
        Create a new email message instance
        """
        # Ensure user_id is set from request context if not provided
        request = self.context.get('request')
        if request and hasattr(request, 'user') and 'user_id' not in validated_data:
            validated_data['user_id'] = request.user.id

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


class EmailAliasSerializer(serializers.ModelSerializer):
    """
    EmailAlias serializer for display and read operations
    """

    full_email_address = serializers.ReadOnlyField()
    user = UserSerializer(read_only=True)

    class Meta:
        model = EmailAlias
        fields = [
            'id', 'alias', 'domain', 'full_email_address',
            'is_active', 'user', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'domain', 'full_email_address',
            'user', 'created_at', 'updated_at'
        ]


class EmailAliasCreateSerializer(serializers.ModelSerializer):
    """
    EmailAlias serializer for create and update operations
    """

    class Meta:
        model = EmailAlias
        fields = ['alias', 'is_active']

    def validate_alias(self, value):
        """Validate alias format and constraints"""
        import re

        # Convert to lowercase for consistency
        value = value.lower().strip()

        # Basic format validation
        if not re.match(r'^[a-zA-Z0-9._-]+$', value):
            raise serializers.ValidationError(
                _('Alias can only contain letters, numbers, dots, '
                  'hyphens, and underscores')
            )

        # Length validation
        if len(value) < 1:
            raise serializers.ValidationError(
                _('Alias cannot be empty')
            )

        if len(value) > 64:
            raise serializers.ValidationError(
                _('Alias cannot be longer than 64 characters')
            )

        # Start/end validation
        if value.startswith('.') or value.endswith('.'):
            raise serializers.ValidationError(
                _('Alias cannot start or end with a dot')
            )

        # Reserved words validation
        reserved_words = [
            'admin', 'administrator', 'root', 'postmaster',
            'webmaster', 'hostmaster', 'noreply', 'no-reply'
        ]

        if value in reserved_words:
            raise serializers.ValidationError(
                _('This alias is reserved and cannot be used')
            )

        return value