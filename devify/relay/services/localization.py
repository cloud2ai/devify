"""Per-delivery localization for Relay artifacts."""

from __future__ import annotations

import json
import logging
from copy import deepcopy
from typing import Any, Dict

from core.tracking import LLMTracker
from relay.models import RelayAppConfig
from threadline.utils.llm import parse_json_response

logger = logging.getLogger(__name__)

LOCALIZATION_METADATA_KEY = "relay_localization"
TRANSLATABLE_FIELDS = (
    "summary_title",
    "summary_content",
    "llm_content",
    "summary_data",
    "todos",
)


def normalize_language(value: Any) -> str:
    """Normalize supported language aliases to their Relay display names."""
    language = str(value or "").strip()
    normalized = language.casefold().replace("_", "-")
    if normalized == "chinese" or normalized.startswith("zh"):
        return "Chinese"
    if normalized == "english" or normalized.startswith("en"):
        return "English"
    return ""


def _cache_localization(delivery, localization: Dict[str, Any]) -> None:
    delivery.metadata = {
        **(getattr(delivery, "metadata", None) or {}),
        LOCALIZATION_METADATA_KEY: localization,
    }
    save = getattr(delivery, "save", None)
    if callable(save):
        save(update_fields=["metadata", "updated_at"])


def _configured_model_uuid() -> str | None:
    app_config = RelayAppConfig.objects.filter(workflow_key="relay").first()
    if app_config and not app_config.is_active:
        raise RuntimeError("Relay localization is disabled")
    if app_config and app_config.llm_config_uuid:
        return str(app_config.llm_config_uuid)
    return None


def _parse_localized_response(response: Any) -> Dict[str, Any]:
    if isinstance(response, dict):
        return response
    if isinstance(response, str):
        return parse_json_response(response)
    raise ValueError("Relay localization returned an unsupported response type")


def _translate_artifact(
    artifact: Dict[str, Any],
    *,
    source_language: str,
    target_language: str,
) -> Dict[str, Any]:
    content = {
        key: artifact[key]
        for key in TRANSLATABLE_FIELDS
        if artifact.get(key) not in (None, "", [], {})
    }
    if not content:
        return {**artifact, "language": target_language}

    prompt = (
        "Localize the supplied Relay delivery artifact into "
        f"{target_language}. Its source language is "
        f"{source_language or 'unknown'}. Translate every human-readable string, including "
        "strings nested in objects and arrays, while preserving JSON structure, "
        "Markdown, URLs, identifiers, issue keys, and technical names. Return only "
        "one JSON object containing exactly the same keys as the supplied artifact. "
        "Do not add commentary."
    )
    response, _usage = LLMTracker.call_and_track(
        prompt=prompt,
        content=json.dumps(content, ensure_ascii=False),
        json_mode=True,
        node_name="relay_localization",
        model_uuid=_configured_model_uuid(),
    )
    translated = _parse_localized_response(response)
    localized = deepcopy(artifact)
    for key, original_value in content.items():
        translated_value = translated.get(key)
        if not isinstance(translated_value, type(original_value)):
            raise ValueError(f"Relay localization omitted or changed type for {key}")
        if isinstance(translated_value, str) and not translated_value.strip():
            raise ValueError(f"Relay localization returned empty text for {key}")
        localized[key] = translated_value
    localized["language"] = target_language
    return localized


def get_delivery_artifact(*, event, subscription, delivery) -> Dict[str, Any]:
    """Return a stable, channel-local artifact without mutating the event snapshot."""
    metadata = getattr(delivery, "metadata", None) or {}
    cached = metadata.get(LOCALIZATION_METADATA_KEY) or {}
    cached_artifact = cached.get("artifact")
    if isinstance(cached_artifact, dict):
        return deepcopy(cached_artifact)

    artifact = deepcopy(getattr(event, "artifact_snapshot", None) or {})
    if not artifact.get("summary_title"):
        artifact["summary_title"] = str(
            getattr(getattr(event, "email_message", None), "subject", "") or ""
        ).strip()

    config = getattr(subscription, "config", None) or {}
    target_language = normalize_language(config.get("language"))
    source_language = normalize_language(artifact.get("language"))
    if not target_language or target_language == source_language:
        return artifact

    status = "localized"
    try:
        localized = _translate_artifact(
            artifact,
            source_language=source_language,
            target_language=target_language,
        )
    except Exception:
        logger.exception(
            "Relay artifact localization failed; using source artifact "
            "delivery=%s target_language=%s",
            getattr(delivery, "id", None),
            target_language,
        )
        localized = artifact
        status = "fallback"

    _cache_localization(
        delivery,
        {
            "status": status,
            "source_language": source_language,
            "target_language": target_language,
            "artifact": localized,
        },
    )
    return deepcopy(localized)
