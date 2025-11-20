"""
EmailMessage Serializers

Serializers for EmailMessage model CRUD operations.
"""

import re

from django.conf import settings
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from ..models import EmailMessage
from .base import UserSerializer
from .email_attachment import (
    EmailAttachmentNestedSerializer,
    EmailAttachmentMinimalSerializer
)
from .email_todo import EmailTodoListSerializer


class EmailMessageSerializer(serializers.ModelSerializer):
    """
    Main serializer for EmailMessage model - used for display
    """

    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    attachments = serializers.SerializerMethodField()
    todos = serializers.SerializerMethodField()

    class Meta:
        model = EmailMessage
        fields = [
            'id', 'uuid', 'user', 'user_id', 'message_id',
            'subject', 'sender', 'recipients', 'received_at',
            'html_content', 'text_content',
            'summary_title', 'summary_content', 'summary_priority',
            'summary_data', 'todos',
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
        return EmailAttachmentNestedSerializer(
            attachments, many=True, context=self.context
        ).data

    def get_todos(self, obj) -> list:
        """
        Get TODOs for this email message

        Returns:
            list: List of TODO data dictionaries
        """
        todos = obj.todos.all().order_by('created_at')
        return EmailTodoListSerializer(
            todos, many=True, context=self.context
        ).data

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

        # Check for duplicate message ID for the same user
        user_id = self.initial_data.get('user_id')
        if user_id:
            queryset = EmailMessage.objects.filter(
                user_id=user_id, message_id=value
            )
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
            from ..state_machine import can_transition_to, EMAIL_STATE_MACHINE

            if not can_transition_to(
                self.instance.status, value, EMAIL_STATE_MACHINE
            ):
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

        # Check if this is a list view by checking if parent serializer
        # has many=True
        is_list_view = self.parent is not None

        # Only limit content for list views to reduce payload size
        # Detail views should return full content
        if is_list_view:
            # Remove large content fields to reduce payload size
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
        # Extract relative path from file_path
        # (supports both email_217/file.jpg and uuid/file.jpg)
        attachment_url_map = {}
        for att in instance.attachments.all():
            if att.is_image and att.file_path:
                rel_path = att.file_path.replace(
                    settings.EMAIL_ATTACHMENT_DIR + '/',
                    ''
                ).lstrip('/')

                # Generate URL
                if settings.ATTACHMENT_BASE_URL:
                    url = (
                        f"{settings.ATTACHMENT_BASE_URL}/attachments/"
                        f"{rel_path}"
                    )
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


class EmailMessageListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for list views - only essential fields
    """

    status_display = serializers.CharField(
        source='get_status_display', read_only=True)
    attachments_count = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()

    class Meta:
        model = EmailMessage
        fields = [
            'id', 'uuid', 'message_id',
            'subject', 'sender', 'recipients', 'received_at',
            'summary_title', 'summary_content', 'summary_priority',
            'status', 'status_display',
            'attachments_count', 'attachments',
            'metadata', 'created_at'
        ]
        read_only_fields = [
            'id', 'uuid', 'status', 'created_at'
        ]

    def get_attachments_count(self, obj):
        """Return count of attachments"""
        return obj.attachments.count()

    def get_attachments(self, obj):
        """Return minimal attachment info"""
        attachments = obj.attachments.all()
        return EmailAttachmentMinimalSerializer(attachments, many=True).data

    def to_representation(self, instance):
        """Limit summary_content length for list views"""
        data = super().to_representation(instance)

        # Limit summary_content for preview
        if data.get('summary_content'):
            max_length = 500
            if len(data['summary_content']) > max_length:
                data['summary_content'] = (
                    data['summary_content'][:max_length] + '...'
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
            'recipients', 'received_at', 'html_content',
            'text_content'
        ]

    def validate_user_id(self, value):
        """
        Validate user exists and set from request context
        """
        # Auto-set user from request
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            return request.user.id

        if value is None:
            raise serializers.ValidationError(
                _("User ID is required")
            )

        try:
            User.objects.get(id=value)
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
        if (request and hasattr(request, 'user') and
                'user_id' not in validated_data):
            validated_data['user_id'] = request.user.id

        return super().create(validated_data)


class EmailMessageUpdateSerializer(serializers.ModelSerializer):
    """
    Update serializer for EmailMessage model
    """

    class Meta:
        model = EmailMessage
        fields = [
            'subject', 'sender', 'recipients',
            'html_content', 'text_content', 'summary_title',
            'summary_content', 'summary_priority', 'summary_data',
            'llm_content', 'status', 'error_message'
        ]
