"""
Issue Serializers

Serializers for Issue model CRUD operations.
"""

from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from ..models import Issue
from .base import UserSerializer


class IssueSerializer(serializers.ModelSerializer):
    """
    Main serializer for Issue model - used for display
    """

    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)
    # Use SerializerMethodField to avoid circular import
    email_message = serializers.SerializerMethodField()
    email_message_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Issue
        fields = [
            'id', 'user', 'user_id', 'email_message', 'email_message_id',
            'title', 'description', 'priority', 'engine', 'external_id',
            'issue_url', 'metadata', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

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
        from ..models import EmailMessage
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
        valid_engines = [
            'jira', 'email', 'slack', 'github', 'gitlab', 'trello'
        ]
        if value.lower() not in valid_engines:
            engines_str = ', '.join(valid_engines)
            raise serializers.ValidationError(
                _("Engine must be one of: {}").format(engines_str)
            )

        return value.lower()

    def validate_priority(self, value):
        """
        Validate priority level
        """
        valid_priorities = [
            'low', 'medium', 'high', 'critical', 'urgent'
        ]
        if value.lower() not in valid_priorities:
            priorities_str = ', '.join(valid_priorities)
            raise serializers.ValidationError(
                _("Priority must be one of: {}").format(priorities_str)
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
        # Auto-set user from request
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            return request.user.id

        try:
            User.objects.get(id=value)
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
