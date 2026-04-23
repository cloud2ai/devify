"""Bridge helpers for resolving agentcore-backed runtime config."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def ensure_default_llm_config():
    """
    Ensure an active global LLMConfig exists for agentcore-metering.

    The project now relies on DB-backed agentcore configuration. This helper
    only resolves an existing config; it does not seed from Django settings.
    """
    try:
        from agentcore_metering.adapters.django.models import LLMConfig
    except Exception as exc:
        logger.debug("agentcore_metering not available: %s", exc)
        return None

    try:
        from agentcore_metering.adapters.django.services.config_source import (
            get_default_llm_config_uuid,
        )
        from threadline.services.workflow_config import (
            get_threadline_workflow_config,
            update_threadline_workflow_config,
        )
    except Exception as exc:
        logger.debug("threadline workflow config service unavailable: %s", exc)
        get_threadline_workflow_config = None  # type: ignore[assignment]
        update_threadline_workflow_config = None  # type: ignore[assignment]
        get_default_llm_config_uuid = None  # type: ignore[assignment]

    try:
        if get_threadline_workflow_config is not None:
            workflow_config = get_threadline_workflow_config()
            seeded_llm = _safe_llm_config_from_uuid(
                LLMConfig,
                workflow_config.text_llm_config_uuid
                or workflow_config.image_llm_config_uuid
                or workflow_config.llm_config_uuid,
            )
            if seeded_llm:
                return seeded_llm

        existing = (
            LLMConfig.objects.filter(
                scope=LLMConfig.Scope.GLOBAL,
                model_type=LLMConfig.MODEL_TYPE_LLM,
                is_active=True,
            )
            .order_by("-is_default", "created_at", "id")
            .first()
        )
        if existing:
            return existing

        default_uuid = (
            get_default_llm_config_uuid()
            if get_default_llm_config_uuid
            else None
        )
        if not default_uuid:
            logger.warning(
                "Skipping agentcore LLM seed because no DB-backed default "
                "config exists"
            )
            return None

        row = _safe_llm_config_from_uuid(LLMConfig, default_uuid)
        if row:
            if update_threadline_workflow_config is not None:
                update_threadline_workflow_config(llm_config_uuid=row.uuid)
            logger.info("Resolved default agentcore LLM config from DB")
        return row
    except Exception as exc:
        logger.debug("Failed to seed agentcore LLM config: %s", exc)
        return None


def _safe_llm_config_from_uuid(model_cls, uuid_value):
    if not uuid_value:
        return None
    try:
        return model_cls.objects.filter(uuid=uuid_value).first()
    except Exception as exc:
        logger.debug(
            "Failed to resolve LLMConfig uuid=%s: %s",
            uuid_value,
            exc,
        )
        return None
