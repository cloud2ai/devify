"""
Serializers for threadline admin APIs.
"""

from __future__ import annotations

from uuid import UUID

from rest_framework import serializers
from agentcore_notifier.constants import Provider


class ThreadlineWorkflowConfigSerializer(serializers.Serializer):
    workflow_key = serializers.CharField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    task_config = serializers.DictField(read_only=True)
    llm_config_uuid = serializers.CharField(allow_null=True, read_only=True)
    image_llm_config_uuid = serializers.CharField(
        allow_null=True,
        read_only=True,
    )
    text_llm_config_uuid = serializers.CharField(
        allow_null=True,
        read_only=True,
    )
    notification_channel_uuid = serializers.CharField(
        allow_null=True,
        read_only=True,
    )
    llm_config = serializers.DictField(allow_null=True, required=False)
    image_llm_config = serializers.DictField(allow_null=True, required=False)
    text_llm_config = serializers.DictField(allow_null=True, required=False)
    notification_channel = serializers.DictField(
        allow_null=True,
        required=False,
    )
    created_at = serializers.DateTimeField(allow_null=True, read_only=True)
    updated_at = serializers.DateTimeField(allow_null=True, read_only=True)


class ThreadlineWorkflowConfigUpdateSerializer(serializers.Serializer):
    llm_config_uuid = serializers.UUIDField(
        allow_null=True,
        required=False,
    )
    image_llm_config_uuid = serializers.UUIDField(
        allow_null=True,
        required=False,
    )
    text_llm_config_uuid = serializers.UUIDField(
        allow_null=True,
        required=False,
    )
    notification_channel_uuid = serializers.UUIDField(
        allow_null=True,
        required=False,
    )
    task_config = serializers.DictField(required=False)
    is_active = serializers.BooleanField(required=False)

    def _get_llm_config(self, value: UUID):
        try:
            from agentcore_metering.adapters.django.models import LLMConfig
        except Exception as exc:
            raise serializers.ValidationError(
                "LLM configuration backend is unavailable."
            ) from exc

        llm_config = LLMConfig.objects.filter(uuid=value).first()
        if not llm_config:
            raise serializers.ValidationError("LLM config not found.")
        return llm_config

    def _validate_llm_config_uuid(self, value: UUID | None):
        if value is None:
            return None
        self._get_llm_config(value)
        return value

    def validate_llm_config_uuid(self, value: UUID | None):
        return self._validate_llm_config_uuid(value)

    def validate_image_llm_config_uuid(self, value: UUID | None):
        return self._validate_llm_config_uuid(value)

    def validate_text_llm_config_uuid(self, value: UUID | None):
        return self._validate_llm_config_uuid(value)

    def validate_notification_channel_uuid(self, value: UUID | None):
        if value is None:
            return None
        try:
            from agentcore_notifier.adapters.django.models import (
                NotificationChannel,
            )
        except Exception as exc:
            raise serializers.ValidationError(
                "Notification backend is unavailable."
            ) from exc

        channel = NotificationChannel.objects.filter(uuid=value).first()
        if not channel:
            raise serializers.ValidationError(
                "Notification channel not found."
            )
        if channel.channel_type != NotificationChannel.TYPE_WEBHOOK:
            raise serializers.ValidationError(
                "Notification channel must be a webhook channel."
            )
        provider_type = str((channel.config or {}).get("provider_type") or "")
        if provider_type.strip().lower() != Provider.FEISHU:
            raise serializers.ValidationError(
                "Notification channel must be a Feishu webhook channel."
            )
        return value
