"""Background sync helpers for legacy Threadline delivery settings."""

from __future__ import annotations

import logging
from typing import Any, Dict

from django.contrib.auth import get_user_model
from django.db import transaction

from agentcore_task.adapters.django import acquire_task_lock, release_task_lock
from relay.models import RelaySubscription
from threadline.models import Settings
from threadline.utils.issues.issue_factory import normalize_issue_engine

logger = logging.getLogger(__name__)

User = get_user_model()

LEGACY_SYNC_LOCK_NAME = "relay_legacy_issue_config_sync"
LEGACY_SUBSCRIPTION_NAMES = {
    "jira": "Legacy Jira Channel",
    "feishu_bitable": "Legacy Feishu Channel",
}
LEGACY_SETTING_KEYS = (
    "issue_config",
    "jira_config",
    "feishu_bitable_config",
)


def _load_legacy_settings(user) -> dict[str, dict]:
    settings = (
        Settings.objects.filter(
            user=user,
            key__in=LEGACY_SETTING_KEYS,
            is_active=True,
        )
        .order_by("key", "-updated_at", "-id")
    )
    legacy_settings: dict[str, dict] = {}
    for setting in settings:
        if isinstance(setting.value, dict) and setting.key not in legacy_settings:
            legacy_settings[setting.key] = setting.value
    return legacy_settings


def _build_subscription_payload(
    setting_key: str, legacy_config: dict
) -> dict | None:
    if not isinstance(legacy_config, dict):
        return None

    if setting_key == "issue_config":
        target_type = normalize_issue_engine(
            legacy_config.get("issue_engine", "jira")
        )
        if target_type not in LEGACY_SUBSCRIPTION_NAMES:
            return None

        if target_type == "feishu_bitable":
            field_mappings = (
                legacy_config.get("feishu_bitable", {}).get(
                    "field_mappings", {}
                )
                if isinstance(legacy_config.get("feishu_bitable"), dict)
                else {}
            )
        else:
            field_mappings = {}

        return {
            "target_type": target_type,
            "name": LEGACY_SUBSCRIPTION_NAMES[target_type],
            "enabled": bool(legacy_config.get("enable", False)),
            "config": legacy_config,
            "strategies": {
                "auto_merge_strategy": legacy_config.get(
                    "auto_merge_strategy", "new"
                ),
                "manual_merge_strategy": legacy_config.get(
                    "manual_merge_strategy", "linked"
                ),
                "retry_issue_strategy": legacy_config.get(
                    "retry_issue_strategy", "update"
                ),
            },
            "field_mappings": field_mappings or {},
        }

    if setting_key == "jira_config":
        return {
            "target_type": "jira",
            "name": LEGACY_SUBSCRIPTION_NAMES["jira"],
            "enabled": True,
            "config": {
                "issue_engine": "jira",
                "enable": True,
                "jira": legacy_config,
            },
            "strategies": {
                "auto_merge_strategy": legacy_config.get(
                    "auto_merge_strategy", "new"
                ),
                "manual_merge_strategy": legacy_config.get(
                    "manual_merge_strategy", "linked"
                ),
                "retry_issue_strategy": legacy_config.get(
                    "retry_issue_strategy", "update"
                ),
            },
            "field_mappings": legacy_config.get("field_mappings", {}) or {},
        }

    if setting_key == "feishu_bitable_config":
        return {
            "target_type": "feishu_bitable",
            "name": LEGACY_SUBSCRIPTION_NAMES["feishu_bitable"],
            "enabled": True,
            "config": {
                "issue_engine": "feishu_bitable",
                "enable": True,
                "feishu_bitable": legacy_config,
            },
            "strategies": {
                "auto_merge_strategy": legacy_config.get(
                    "auto_merge_strategy", "new"
                ),
                "manual_merge_strategy": legacy_config.get(
                    "manual_merge_strategy", "linked"
                ),
                "retry_issue_strategy": legacy_config.get(
                    "retry_issue_strategy", "update"
                ),
            },
            "field_mappings": legacy_config.get("field_mappings", {}) or {},
        }

    return None


def sync_legacy_channels_for_user(user) -> dict:
    """Sync a user's legacy Threadline channel settings into Relay."""
    legacy_settings = _load_legacy_settings(user)
    if not legacy_settings:
        return {"status": "skipped", "reason": "missing_legacy_settings"}

    created = 0
    updated = 0
    skipped = 0
    synced_subscriptions: list[dict[str, Any]] = []

    legacy_items: list[tuple[str, dict]] = []
    if "issue_config" in legacy_settings:
        legacy_items.append(("issue_config", legacy_settings["issue_config"]))
    else:
        for key in ("jira_config", "feishu_bitable_config"):
            if key in legacy_settings:
                legacy_items.append((key, legacy_settings[key]))

    with transaction.atomic():
        for setting_key, legacy_config in legacy_items:
            payload = _build_subscription_payload(setting_key, legacy_config)
            if not payload:
                skipped += 1
                continue

            subscription, created_flag = RelaySubscription.objects.update_or_create(
                user=user,
                target_type=payload["target_type"],
                name=payload["name"],
                defaults={
                    "enabled": payload["enabled"],
                    "config": payload["config"],
                    "strategies": payload["strategies"],
                    "field_mappings": payload["field_mappings"],
                },
            )
            created += 1 if created_flag else 0
            updated += 0 if created_flag else 1
            synced_subscriptions.append(
                {
                    "setting_key": setting_key,
                    "subscription_id": subscription.id,
                    "target_type": subscription.target_type,
                    "name": subscription.name,
                    "created": created_flag,
                }
            )

    if not synced_subscriptions:
        return {
            "status": "skipped",
            "reason": "unsupported_legacy_settings",
            "user_id": user.id,
        }

    return {
        "status": "success",
        "user_id": user.id,
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "subscriptions": synced_subscriptions,
    }


def sync_all_legacy_channels() -> dict:
    """Sync legacy Threadline channel settings for all users once."""
    if not acquire_task_lock(LEGACY_SYNC_LOCK_NAME, timeout=300):
        logger.info(
            "Skipping relay legacy sync because another worker holds the lock"
        )
        return {
            "status": "skipped",
            "reason": "legacy_sync_lock_exists",
            "created": 0,
            "exists": 0,
            "skipped": 0,
        }

    try:
        created = 0
        updated = 0
        skipped = 0
        errors: list[dict[str, Any]] = []

        users = (
            User.objects.filter(
                settings__key__in=LEGACY_SETTING_KEYS,
                settings__is_active=True,
            )
            .distinct()
            .order_by("id")
        )

        for user in users:
            try:
                result = sync_legacy_channels_for_user(user)
                created += int(result.get("created", 0))
                updated += int(result.get("updated", 0))
                skipped += int(result.get("skipped", 0))
            except Exception as exc:
                logger.exception(
                    "Failed to sync legacy relay config for user %s: %s",
                    user.id,
                    exc,
                )
                errors.append(
                    {
                        "user_id": user.id,
                        "error": str(exc),
                    }
                )

        return {
            "status": "success",
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "errors": errors,
        }
    finally:
        release_task_lock(LEGACY_SYNC_LOCK_NAME)


def sync_legacy_issue_config_for_user(user) -> dict:
    """Backward compatible alias for issue-config based sync callers."""
    return sync_legacy_channels_for_user(user)


def sync_all_legacy_issue_configs() -> dict:
    """Backward compatible alias for legacy background startup sync."""
    return sync_all_legacy_channels()
