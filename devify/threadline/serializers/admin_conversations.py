"""Admin conversation serializers."""

from rest_framework import serializers

from agentcore_task.adapters.django.models import TaskExecution

from ..models import EmailMessage
from .base import UserSerializer


class AdminConversationListSerializer(serializers.ModelSerializer):
    """
    Admin-focused message list serializer with nested user data.
    """

    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    user_display = serializers.SerializerMethodField()
    relay_delivery_count = serializers.IntegerField(read_only=True)
    is_canonical = serializers.SerializerMethodField()

    class Meta:
        model = EmailMessage
        fields = [
            "id",
            "uuid",
            "message_id",
            "subject",
            "summary_title",
            "summary_content",
            "text_content",
            "sender",
            "recipients",
            "received_at",
            "status",
            "user",
            "user_id",
            "user_display",
            "relay_delivery_count",
            "is_canonical",
            "created_at",
        ]
        read_only_fields = fields + [
            "user",
            "user_id",
            "user_display",
            "relay_delivery_count",
            "is_canonical",
        ]

    def get_user_display(self, obj):
        user = getattr(obj, "user", None)
        if not user:
            return None
        if user.first_name and user.last_name:
            return f"{user.first_name} {user.last_name}"
        if user.first_name:
            return user.first_name
        if user.last_name:
            return user.last_name
        return user.username

    def get_is_canonical(self, obj):
        return obj.merged_into_id is None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        max_length = 500
        for field in ("summary_content", "text_content"):
            if data.get(field) and len(data[field]) > max_length:
                data[field] = f"{data[field][:max_length]}..."
        return data


class AdminConversationTaskListSerializer(serializers.ModelSerializer):
    """
    Lightweight task execution serializer for conversation task lists.

    Keeps the list endpoint fast by excluding heavy JSON/log fields that are
    only needed in the task detail drawer.
    """

    duration = serializers.ReadOnlyField()
    is_completed = serializers.ReadOnlyField()
    is_running = serializers.ReadOnlyField()
    created_by_username = serializers.CharField(
        source="created_by.username", read_only=True
    )
    created_by_id = serializers.IntegerField(
        source="created_by.id", read_only=True
    )

    class Meta:
        model = TaskExecution
        fields = [
            "id",
            "task_id",
            "task_name",
            "module",
            "status",
            "created_at",
            "started_at",
            "finished_at",
            "created_by_id",
            "created_by_username",
            "duration",
            "is_completed",
            "is_running",
        ]
