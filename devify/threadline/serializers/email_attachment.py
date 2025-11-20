"""
EmailAttachment Serializers

Serializers for EmailAttachment model CRUD operations.
"""

import re

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from ..models import EmailAttachment


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


class EmailAttachmentMinimalSerializer(serializers.ModelSerializer):
    """
    Minimal attachment serializer for list views - only metadata
    """

    class Meta:
        model = EmailAttachment
        fields = ['id', 'filename', 'content_type',
                  'file_size', 'is_image', 'safe_filename']
        read_only_fields = ['id']


class EmailAttachmentSerializer(serializers.ModelSerializer):
    """
    Main serializer for EmailAttachment model - used for display
    """

    # Use SerializerMethodField to avoid circular import
    email_message = serializers.SerializerMethodField()
    email_message_id = serializers.IntegerField(write_only=True)
    status_display = serializers.CharField(
        source='get_status_display', read_only=True)

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

    def get_email_message(self, obj):
        """
        Get email message serialized data
        """
        from .email_message import EmailMessageSerializer
        if obj.email_message:
            return EmailMessageSerializer(
                obj.email_message,
                context=self.context
            ).data
        return None

    def validate_email_message_id(self, value):
        """
        Validate email message exists
        """
        from ..models import EmailMessage
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
