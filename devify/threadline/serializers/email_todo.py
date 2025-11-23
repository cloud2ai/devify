"""
EmailTodo Serializers

Serializers for EmailTodo model CRUD operations.
"""

from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from ..models import EmailTodo, EmailMessage
from .base import UserSerializer


class EmailTodoFilterSerializer(serializers.Serializer):
    """
    Filter serializer for TODO list query parameters
    """
    is_completed = serializers.BooleanField(required=False)
    email_message_id = serializers.IntegerField(required=False)
    priority = serializers.ChoiceField(
        choices=['high', 'medium', 'low'],
        required=False
    )
    owner = serializers.CharField(required=False)
    deadline_before = serializers.DateTimeField(required=False)
    deadline_after = serializers.DateTimeField(required=False)


class EmailTodoListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for TODO list views
    """
    email_message_id = serializers.IntegerField(
        source='email_message.id',
        read_only=True
    )
    email_message_subject = serializers.CharField(
        source='email_message.subject',
        read_only=True,
        allow_null=True
    )
    email_message_summary_title = serializers.CharField(
        source='email_message.summary_title',
        read_only=True,
        allow_null=True
    )
    email_message_metadata = serializers.JSONField(
        source='email_message.metadata',
        read_only=True,
        allow_null=True
    )
    # Nested email_message object for easier access
    email_message = serializers.SerializerMethodField()

    class Meta:
        model = EmailTodo
        fields = [
            'id', 'content', 'is_completed', 'completed_at', 'priority',
            'owner', 'deadline', 'location', 'email_message_id',
            'email_message_subject', 'email_message_summary_title',
            'email_message_metadata', 'email_message', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'completed_at']

    def get_email_message(self, obj):
        """
        Get minimal email message data for grouping
        """
        if obj.email_message:
            return {
                'id': obj.email_message.id,
                'subject': obj.email_message.subject,
                'summary_title': obj.email_message.summary_title,
                'metadata': obj.email_message.metadata or {}
            }
        return None


class EmailTodoSerializer(serializers.ModelSerializer):
    """
    Main serializer for EmailTodo model - used for display and updates
    """
    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True, required=False)
    # Use SerializerMethodField to avoid circular import
    email_message = serializers.SerializerMethodField()
    email_message_id = serializers.IntegerField(
        write_only=True,
        required=False,
        allow_null=True
    )

    class Meta:
        model = EmailTodo
        fields = [
            'id', 'user', 'user_id', 'email_message', 'email_message_id',
            'content', 'is_completed', 'completed_at', 'priority', 'owner',
            'deadline', 'location', 'metadata', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'completed_at']

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

        # Check if user can access this TODO
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            if request.user != user and not request.user.is_superuser:
                raise serializers.ValidationError(
                    _("You can only create TODOs for yourself")
                )

        return value

    def validate_email_message_id(self, value):
        """
        Validate email message exists and belongs to the user (if provided)
        """
        # Allow None for manually created TODOs
        if value is None:
            return value

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

    def validate_priority(self, value):
        """
        Validate priority level
        """
        if value and value.lower() not in ['high', 'medium', 'low']:
            raise serializers.ValidationError(
                _("Priority must be one of: high, medium, low")
            )
        return value.lower() if value else None

    def validate(self, attrs):
        """
        Object-level validation
        """
        # Set user_id from request if not provided
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            if 'user_id' not in attrs:
                attrs['user_id'] = request.user.id

        # Set completed_at when marking as completed
        if attrs.get('is_completed') and not self.instance:
            # New TODO being created as completed
            attrs['completed_at'] = timezone.now()
        elif attrs.get('is_completed') and self.instance:
            # Existing TODO being marked as completed
            if not self.instance.is_completed:
                attrs['completed_at'] = timezone.now()
        elif not attrs.get('is_completed', True):
            # Marking as incomplete
            attrs['completed_at'] = None

        return attrs

    def create(self, validated_data):
        """
        Create EmailTodo instance
        """
        user_id = validated_data.pop('user_id')
        email_message_id = validated_data.pop('email_message_id', None)

        user = User.objects.get(id=user_id)
        email_message = None
        if email_message_id:
            email_message = EmailMessage.objects.get(id=email_message_id)

        todo = EmailTodo.objects.create(
            user=user,
            email_message=email_message,
            **validated_data
        )
        return todo

    def update(self, instance, validated_data):
        """
        Update EmailTodo instance
        """
        validated_data.pop('user_id', None)
        validated_data.pop('email_message_id', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
