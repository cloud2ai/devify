"""Relay API serializers."""

from __future__ import annotations

from uuid import UUID

from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from relay.models import (
    RelayAppConfig,
    RelayDelivery,
    RelayEvent,
    RelaySubscription,
)


User = get_user_model()


def _resolve_canonical_email_message(message):
    """
    Resolve the root email message for a merge cluster.

    Relay cards should treat merged siblings as one related problem group.
    The retry action always targets the newest event in that group, but the
    grouping key needs to stay anchored to the canonical root message.
    """

    current = message
    visited: set[int] = set()

    while current and current.merged_into_id and current.id not in visited:
        visited.add(current.id)
        if current.merged_into_id and current.merged_into:
            current = current.merged_into
            continue
        break

    return current or message


class RelaySubscriptionSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = RelaySubscription
        fields = [
            "id",
            "user_id",
            "target_type",
            "name",
            "enabled",
            "config",
            "strategies",
            "field_mappings",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_user_id(self, value):
        request = self.context.get("request")
        if request and request.user and not request.user.is_superuser:
            if int(value) != request.user.id:
                raise serializers.ValidationError(
                    _("You can only manage your own subscriptions")
                )
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError(_("User does not exist"))
        return value

    def validate_config(self, value):
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError(_("Config must be an object"))
        return value

    def validate_strategies(self, value):
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError(_("Strategies must be an object"))
        return value

    def validate_field_mappings(self, value):
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError(
                _("Field mappings must be an object")
            )
        return value

    def validate(self, attrs):
        request = self.context.get("request")
        if (
            self.instance is None
            and request
            and request.user
            and request.user.is_superuser
            and "user_id" not in attrs
        ):
            raise serializers.ValidationError(
                {"user_id": _("user_id is required when creating as superuser")}
            )
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user and not request.user.is_superuser:
            validated_data["user"] = request.user
        else:
            user_id = validated_data.pop("user_id", None)
            if user_id is not None:
                validated_data["user_id"] = user_id
        validated_data.setdefault("config", {})
        validated_data.setdefault("strategies", {})
        validated_data.setdefault("field_mappings", {})
        return super().create(validated_data)


class RelayDeliverySerializer(serializers.ModelSerializer):
    subscription = RelaySubscriptionSerializer(read_only=True)
    event_artifact_snapshot = serializers.SerializerMethodField()
    email_subject = serializers.CharField(
        source="event.email_message.subject",
        read_only=True,
    )

    class Meta:
        model = RelayDelivery
        fields = [
            "id",
            "event",
            "subscription",
            "target_type",
            "status",
            "external_id",
            "external_url",
            "error_message",
            "metadata",
            "agentcore_task_id",
            "idempotency_key",
            "event_artifact_snapshot",
            "email_subject",
            "created_at",
            "updated_at",
        ]

    def get_event_artifact_snapshot(self, obj):
        snapshot = getattr(obj.event, "artifact_snapshot", None) or {}
        return snapshot


class RelayDeliverySummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = RelayDelivery
        fields = [
            "id",
            "target_type",
            "status",
            "external_id",
            "external_url",
            "error_message",
            "agentcore_task_id",
            "created_at",
            "updated_at",
        ]


class RelayEventListSerializer(serializers.ModelSerializer):
    deliveries = RelayDeliverySummarySerializer(many=True, read_only=True)
    delivery_count = serializers.SerializerMethodField()
    failed_delivery_count = serializers.SerializerMethodField()
    event_artifact_snapshot = serializers.SerializerMethodField()
    email_message_uuid = serializers.SerializerMethodField()
    email_message_subject = serializers.SerializerMethodField()
    email_message_summary_title = serializers.SerializerMethodField()
    email_message_merged_into_uuid = serializers.SerializerMethodField()
    email_message_root_uuid = serializers.SerializerMethodField()
    email_message_root_subject = serializers.SerializerMethodField()
    email_message_root_summary_title = serializers.SerializerMethodField()

    class Meta:
        model = RelayEvent
        fields = [
            "id",
            "user",
            "email_message",
            "email_message_uuid",
            "email_message_subject",
            "email_message_summary_title",
            "email_message_merged_into_uuid",
            "email_message_root_uuid",
            "email_message_root_subject",
            "email_message_root_summary_title",
            "event_type",
            "artifact_snapshot",
            "event_artifact_snapshot",
            "status",
            "processed_at",
            "deliveries",
            "delivery_count",
            "failed_delivery_count",
            "created_at",
        ]

    def get_delivery_count(self, obj):
        return len(getattr(obj, "deliveries", []).all())

    def get_failed_delivery_count(self, obj):
        return sum(
            1
            for delivery in getattr(obj, "deliveries", []).all()
            if delivery.status == RelayDelivery.Status.FAILED
        )

    def get_event_artifact_snapshot(self, obj):
        return getattr(obj, "artifact_snapshot", None) or {}

    def get_email_message_uuid(self, obj):
        message = getattr(obj, "email_message", None)
        if message:
            return str(message.uuid)
        return None

    def get_email_message_subject(self, obj):
        message = getattr(obj, "email_message", None)
        if message:
            return message.subject
        return None

    def get_email_message_summary_title(self, obj):
        message = getattr(obj, "email_message", None)
        if message:
            return message.summary_title or message.subject
        return None

    def get_email_message_merged_into_uuid(self, obj):
        message = getattr(obj, "email_message", None)
        if message and message.merged_into_id and message.merged_into:
            return str(message.merged_into.uuid)
        return None

    def get_email_message_root_uuid(self, obj):
        message = getattr(obj, "email_message", None)
        if not message:
            return None
        root = _resolve_canonical_email_message(message)
        return str(root.uuid) if root else None

    def get_email_message_root_subject(self, obj):
        message = getattr(obj, "email_message", None)
        if not message:
            return None
        root = _resolve_canonical_email_message(message)
        return root.subject if root else None

    def get_email_message_root_summary_title(self, obj):
        message = getattr(obj, "email_message", None)
        if not message:
            return None
        root = _resolve_canonical_email_message(message)
        if not root:
            return None
        return root.summary_title or root.subject


class RelayEventSerializer(serializers.ModelSerializer):
    event_artifact_snapshot = serializers.SerializerMethodField()
    email_message_uuid = serializers.SerializerMethodField()
    email_message_subject = serializers.SerializerMethodField()
    email_message_summary_title = serializers.SerializerMethodField()
    email_message_merged_into_uuid = serializers.SerializerMethodField()
    email_message_root_uuid = serializers.SerializerMethodField()
    email_message_root_subject = serializers.SerializerMethodField()
    email_message_root_summary_title = serializers.SerializerMethodField()

    class Meta:
        model = RelayEvent
        fields = [
            "id",
            "user",
            "email_message",
            "email_message_uuid",
            "email_message_subject",
            "email_message_summary_title",
            "email_message_merged_into_uuid",
            "email_message_root_uuid",
            "email_message_root_subject",
            "email_message_root_summary_title",
            "event_type",
            "artifact_snapshot",
            "event_artifact_snapshot",
            "status",
            "processed_at",
            "created_at",
        ]

    def get_email_message_uuid(self, obj):
        message = getattr(obj, "email_message", None)
        if message:
            return str(message.uuid)
        return None

    def get_email_message_subject(self, obj):
        message = getattr(obj, "email_message", None)
        if message:
            return message.subject
        return None

    def get_email_message_summary_title(self, obj):
        message = getattr(obj, "email_message", None)
        if message:
            return message.summary_title or message.subject
        return None

    def get_email_message_merged_into_uuid(self, obj):
        message = getattr(obj, "email_message", None)
        if message and message.merged_into_id and message.merged_into:
            return str(message.merged_into.uuid)
        return None

    def get_email_message_root_uuid(self, obj):
        message = getattr(obj, "email_message", None)
        if not message:
            return None
        root = _resolve_canonical_email_message(message)
        return str(root.uuid) if root else None

    def get_email_message_root_subject(self, obj):
        message = getattr(obj, "email_message", None)
        if not message:
            return None
        root = _resolve_canonical_email_message(message)
        return root.subject if root else None

    def get_email_message_root_summary_title(self, obj):
        message = getattr(obj, "email_message", None)
        if not message:
            return None
        root = _resolve_canonical_email_message(message)
        if not root:
            return None
        return root.summary_title or root.subject

    def get_event_artifact_snapshot(self, obj):
        return getattr(obj, "artifact_snapshot", None) or {}


class RelayAppConfigSerializer(serializers.ModelSerializer):
    llm_config_uuid = serializers.UUIDField(allow_null=True, required=False)

    class Meta:
        model = RelayAppConfig
        fields = [
            "id",
            "workflow_key",
            "llm_config_uuid",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "workflow_key", "created_at", "updated_at"]

    def validate_llm_config_uuid(self, value):
        if value is None:
            return value
        if not isinstance(value, UUID):
            raise serializers.ValidationError(_("Invalid UUID"))
        return value
