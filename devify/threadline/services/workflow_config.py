"""
Runtime bindings for the Threadline workflow.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from django.db import transaction

from threadline.models import ThreadlineWorkflowConfig
from agentcore_notifier.constants import Provider

logger = logging.getLogger(__name__)

THREADLINE_WORKFLOW_KEY = "threadline"


def get_threadline_workflow_config() -> ThreadlineWorkflowConfig:
    """
    Return the singleton Threadline workflow config row.
    """
    obj, _ = ThreadlineWorkflowConfig.objects.get_or_create(
        workflow_key=THREADLINE_WORKFLOW_KEY,
        defaults={"task_config": {}},
    )
    return obj


def _safe_uuid_ref(model_cls, uuid_value):
    if not uuid_value:
        return None
    try:
        return model_cls.objects.filter(uuid=uuid_value).first()
    except Exception as exc:
        logger.debug(
            "Failed to resolve %s uuid=%s: %s", model_cls, uuid_value, exc
        )
        return None


def _effective_text_llm_uuid(config: ThreadlineWorkflowConfig):
    return config.text_llm_config_uuid or config.llm_config_uuid


def _effective_image_llm_uuid(config: ThreadlineWorkflowConfig):
    return config.image_llm_config_uuid or config.llm_config_uuid


def _llm_config_model_class():
    try:
        from agentcore_metering.adapters.django.models import LLMConfig
    except Exception as exc:
        raise RuntimeError(
            "LLM configuration backend is unavailable."
        ) from exc

    return LLMConfig


def resolve_threadline_image_llm_config():
    """
    Resolve the configured image LLMConfig.
    """
    try:
        config = get_threadline_workflow_config()
        llm_model_cls = _llm_config_model_class()
    except RuntimeError as exc:
        logger.debug("agentcore_metering not available: %s", exc)
        return None

    image_uuid = config.image_llm_config_uuid
    if image_uuid:
        return _safe_uuid_ref(llm_model_cls, image_uuid)

    fallback_uuid = config.text_llm_config_uuid or config.llm_config_uuid
    if fallback_uuid:
        return _safe_uuid_ref(llm_model_cls, fallback_uuid)

    return resolve_threadline_llm_config()


def resolve_threadline_text_llm_config():
    """
    Resolve the configured text-processing LLMConfig.
    """
    try:
        config = get_threadline_workflow_config()
        llm_model_cls = _llm_config_model_class()
    except RuntimeError as exc:
        logger.debug("agentcore_metering not available: %s", exc)
        return None

    text_llm_config = _safe_uuid_ref(
        llm_model_cls,
        _effective_text_llm_uuid(config),
    )
    if text_llm_config is not None:
        return text_llm_config

    return resolve_threadline_llm_config()


def resolve_threadline_llm_config():
    """
    Resolve the configured LLMConfig, falling back to the seeded default.

    Legacy compatibility:
    - Prefer the text model binding
    - Fall back to the image model binding
    - Fall back to the legacy single binding
    """
    try:
        config = get_threadline_workflow_config()
        llm_model_cls = _llm_config_model_class()
    except RuntimeError as exc:
        logger.debug("agentcore_metering not available: %s", exc)
        return None

    llm_config = _safe_uuid_ref(
        llm_model_cls,
        _effective_text_llm_uuid(config),
    )
    if llm_config is None:
        llm_config = _safe_uuid_ref(
            llm_model_cls,
            _effective_image_llm_uuid(config),
        )
    if llm_config is not None:
        return llm_config

    try:
        LLMConfig = llm_model_cls
        return (
            LLMConfig.objects.filter(
                scope=LLMConfig.Scope.GLOBAL,
                model_type=LLMConfig.MODEL_TYPE_LLM,
                is_active=True,
            )
            .order_by("-is_default", "created_at", "id")
            .first()
        )
    except Exception as exc:
        logger.debug("Failed to resolve default LLMConfig: %s", exc)
        return None


def resolve_threadline_notification_channel():
    """
    Resolve the configured NotificationChannel, if any.
    """
    try:
        from agentcore_notifier.adapters.django.models import (
            NotificationChannel,
        )
    except Exception as exc:
        logger.debug("agentcore_notifier not available: %s", exc)
        return None

    config = get_threadline_workflow_config()
    channel = _safe_uuid_ref(
        NotificationChannel, config.notification_channel_uuid
    )
    if channel is not None:
        provider_type = str((channel.config or {}).get("provider_type") or "")
        if channel.channel_type == NotificationChannel.TYPE_WEBHOOK and (
            provider_type.strip().lower() == Provider.FEISHU
        ):
            return channel
        logger.warning(
            "Ignoring unsupported Threadline notification channel uuid=%s "
            "provider_type=%s",
            config.notification_channel_uuid,
            provider_type or "<missing>",
        )
    try:
        for candidate in NotificationChannel.objects.filter(
            is_active=True,
            is_default=True,
        ).order_by("created_at"):
            provider_type = str(
                (candidate.config or {}).get("provider_type") or ""
            )
            if (
                candidate.channel_type == NotificationChannel.TYPE_WEBHOOK
                and provider_type.strip().lower() == Provider.FEISHU
            ):
                return candidate
            logger.warning(
                "Skipping unsupported default Threadline notification "
                "channel uuid=%s provider_type=%s",
                candidate.uuid,
                provider_type or "<missing>",
            )
        return None
    except Exception as exc:
        logger.debug("Failed to resolve default NotificationChannel: %s", exc)
        return None


def serialize_threadline_workflow_config() -> Dict[str, Any]:
    """
    Return a payload suitable for the management UI.
    """
    config = get_threadline_workflow_config()
    llm_config = resolve_threadline_llm_config()
    image_llm_config = resolve_threadline_image_llm_config()
    text_llm_config = resolve_threadline_text_llm_config()
    notification_channel = resolve_threadline_notification_channel()

    return {
        "workflow_key": config.workflow_key,
        "is_active": config.is_active,
        "task_config": config.task_config or {},
        "llm_config_uuid": (
            str(
                config.llm_config_uuid
                or _effective_text_llm_uuid(config)
                or _effective_image_llm_uuid(config)
            )
            if (
                config.llm_config_uuid
                or _effective_text_llm_uuid(config)
                or _effective_image_llm_uuid(config)
            )
            else None
        ),
        "image_llm_config_uuid": (
            str(_effective_image_llm_uuid(config))
            if _effective_image_llm_uuid(config)
            else None
        ),
        "text_llm_config_uuid": (
            str(_effective_text_llm_uuid(config))
            if _effective_text_llm_uuid(config)
            else None
        ),
        "notification_channel_uuid": (
            str(config.notification_channel_uuid)
            if config.notification_channel_uuid
            else None
        ),
        "llm_config": (
            {
                "uuid": str(llm_config.uuid),
                "provider": llm_config.provider,
                "model_type": llm_config.model_type,
                "scope": llm_config.scope,
                "user_id": llm_config.user_id,
                "is_active": llm_config.is_active,
                "is_default": llm_config.is_default,
            }
            if llm_config
            else None
        ),
        "image_llm_config": (
            {
                "uuid": str(image_llm_config.uuid),
                "provider": image_llm_config.provider,
                "model_type": image_llm_config.model_type,
                "scope": image_llm_config.scope,
                "user_id": image_llm_config.user_id,
                "is_active": image_llm_config.is_active,
                "is_default": image_llm_config.is_default,
            }
            if image_llm_config
            else None
        ),
        "text_llm_config": (
            {
                "uuid": str(text_llm_config.uuid),
                "provider": text_llm_config.provider,
                "model_type": text_llm_config.model_type,
                "scope": text_llm_config.scope,
                "user_id": text_llm_config.user_id,
                "is_active": text_llm_config.is_active,
                "is_default": text_llm_config.is_default,
            }
            if text_llm_config
            else None
        ),
        "notification_channel": (
            {
                "uuid": str(notification_channel.uuid),
                "channel_type": notification_channel.channel_type,
                "name": notification_channel.name,
                "scope": "user" if notification_channel.user_id else "global",
                "user_id": notification_channel.user_id,
                "is_active": notification_channel.is_active,
                "is_default": notification_channel.is_default,
            }
            if notification_channel
            else None
        ),
        "updated_at": config.updated_at.isoformat()
        if config.updated_at
        else None,
        "created_at": config.created_at.isoformat()
        if config.created_at
        else None,
    }


@transaction.atomic
def update_threadline_workflow_config(
    *,
    llm_config_uuid: Optional[str] = None,
    image_llm_config_uuid: Optional[str] = None,
    text_llm_config_uuid: Optional[str] = None,
    notification_channel_uuid: Optional[str] = None,
    task_config: Optional[Dict[str, Any]] = None,
    is_active: Optional[bool] = None,
) -> ThreadlineWorkflowConfig:
    """
    Update the singleton config row and return it.
    """
    config = get_threadline_workflow_config()

    if llm_config_uuid is not None:
        value = llm_config_uuid or None
        config.llm_config_uuid = value
        config.image_llm_config_uuid = value
        config.text_llm_config_uuid = value
    if image_llm_config_uuid is not None:
        config.image_llm_config_uuid = image_llm_config_uuid or None
    if text_llm_config_uuid is not None:
        config.text_llm_config_uuid = text_llm_config_uuid or None
    if notification_channel_uuid is not None:
        config.notification_channel_uuid = notification_channel_uuid or None
    if task_config is not None:
        config.task_config = task_config or {}
    if is_active is not None:
        config.is_active = bool(is_active)

    if config.text_llm_config_uuid or config.image_llm_config_uuid:
        config.llm_config_uuid = (
            config.text_llm_config_uuid or config.image_llm_config_uuid
        )
    else:
        config.llm_config_uuid = None

    config.save()
    return config
