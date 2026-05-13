"""Backfill legacy Threadline Issue records into Relay history tables."""

from __future__ import annotations

import logging
from typing import Any

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from agentcore_task.adapters.django import acquire_task_lock, release_task_lock
from relay.models import RelayDelivery, RelayEvent, RelaySubscription
from relay.services.legacy_sync import (
    LEGACY_SUBSCRIPTION_NAMES,
    _build_subscription_payload,
    _load_legacy_settings,
)
from threadline.models import Issue
from threadline.utils.issues.issue_factory import normalize_issue_engine

logger = logging.getLogger(__name__)

User = get_user_model()

LEGACY_ISSUE_SYNC_LOCK_NAME = "relay_legacy_issue_history_sync"
DEFAULT_STRATEGIES = {
    "auto_merge_strategy": "new",
    "manual_merge_strategy": "linked",
    "retry_issue_strategy": "update",
}


def _issue_snapshot(issue: Issue) -> dict[str, Any]:
    return {
        "legacy_issue_id": issue.id,
        "title": issue.title,
        "description": issue.description,
        "priority": issue.priority,
        "engine": issue.engine,
        "external_id": issue.external_id,
        "issue_url": issue.issue_url,
        "metadata": issue.metadata or {},
        "source": {
            "email_message_id": issue.email_message_id,
            "user_id": issue.user_id,
        },
        "created_at": issue.created_at.isoformat() if issue.created_at else None,
        "updated_at": issue.updated_at.isoformat() if issue.updated_at else None,
    }


def _legacy_subscription_for_issue(
    issue: Issue,
    legacy_settings: dict[str, dict] | None = None,
) -> RelaySubscription | None:
    target_type = normalize_issue_engine(issue.engine)
    if target_type not in LEGACY_SUBSCRIPTION_NAMES:
        return None

    payload = None
    if legacy_settings:
        if "issue_config" in legacy_settings:
            payload = _build_subscription_payload(
                "issue_config", legacy_settings["issue_config"]
            )
        else:
            legacy_key = f"{target_type}_config"
            if legacy_key in legacy_settings:
                payload = _build_subscription_payload(
                    legacy_key, legacy_settings[legacy_key]
                )

    subscription = (
        RelaySubscription.objects.filter(
            user=issue.user,
            target_type=target_type,
        )
        .order_by("created_at", "id")
        .first()
    )
    if subscription:
        if payload and payload.get("strategies") and not subscription.strategies:
            subscription.strategies = payload["strategies"]
            subscription.save(update_fields=["strategies", "updated_at"])
        elif not subscription.strategies:
            subscription.strategies = DEFAULT_STRATEGIES.copy()
            subscription.save(update_fields=["strategies", "updated_at"])
        return subscription

    return RelaySubscription.objects.create(
        user=issue.user,
        target_type=target_type,
        name=LEGACY_SUBSCRIPTION_NAMES[target_type],
        enabled=True,
        config={},
        strategies=(payload["strategies"] if payload and payload.get("strategies") else DEFAULT_STRATEGIES.copy()),
        field_mappings={},
    )


def sync_legacy_issues_for_user(user) -> dict:
    """Backfill a user's legacy Issue rows into Relay event history."""
    issues = (
        Issue.objects.filter(user=user)
        .select_related("email_message")
        .order_by("id")
    )
    if not issues.exists():
        return {"status": "skipped", "reason": "missing_legacy_issues"}

    created = 0
    updated = 0
    skipped = 0
    synced_items: list[dict[str, Any]] = []
    legacy_settings = _load_legacy_settings(user)

    with transaction.atomic():
        for issue in issues:
            subscription = _legacy_subscription_for_issue(
                issue,
                legacy_settings=legacy_settings,
            )
            if not subscription:
                skipped += 1
                continue

            idempotency_key = f"legacy_issue:{issue.id}"
            existing_delivery = RelayDelivery.objects.filter(
                idempotency_key=idempotency_key
            ).select_related("event", "subscription").first()
            if existing_delivery:
                skipped += 1
                continue

            event = RelayEvent.objects.create(
                user=issue.user,
                email_message=issue.email_message,
                event_type=RelayEvent.EventType.WORKFLOW_COMPLETED,
                artifact_snapshot=_issue_snapshot(issue),
                status=RelayEvent.Status.COMPLETED,
                processed_at=timezone.now(),
            )
            delivery = RelayDelivery.objects.create(
                event=event,
                subscription=subscription,
                target_type=subscription.target_type,
                status=RelayDelivery.Status.SUCCESS,
                external_id=issue.external_id,
                external_url=issue.issue_url,
                error_message="",
                metadata={
                    "legacy_issue_id": issue.id,
                    "legacy_issue_engine": issue.engine,
                    "legacy_issue_metadata": issue.metadata or {},
                },
                agentcore_task_id="",
                idempotency_key=idempotency_key,
            )
            created += 1
            synced_items.append(
                {
                    "issue_id": issue.id,
                    "event_id": event.id,
                    "delivery_id": delivery.id,
                    "target_type": subscription.target_type,
                }
            )

    if not synced_items:
        return {
            "status": "skipped",
            "reason": "unsupported_legacy_issues",
            "user_id": user.id,
        }

    return {
        "status": "success",
        "user_id": user.id,
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "issues": synced_items,
    }


def sync_all_legacy_issues() -> dict:
    """Backfill legacy Issue rows for all users once."""
    if not acquire_task_lock(LEGACY_ISSUE_SYNC_LOCK_NAME, timeout=300):
        logger.info(
            "Skipping legacy issue sync because another worker holds the lock"
        )
        return {
            "status": "skipped",
            "reason": "legacy_issue_sync_lock_exists",
            "created": 0,
            "updated": 0,
            "skipped": 0,
        }

    try:
        created = 0
        updated = 0
        skipped = 0
        errors: list[dict[str, Any]] = []

        users = (
            User.objects.filter(issues__isnull=False)
            .distinct()
            .order_by("id")
        )

        for user in users:
            try:
                result = sync_legacy_issues_for_user(user)
                created += int(result.get("created", 0))
                updated += int(result.get("updated", 0))
                skipped += int(result.get("skipped", 0))
            except Exception as exc:
                logger.exception(
                    "Failed to sync legacy issues for user %s: %s",
                    user.id,
                    exc,
                )
                errors.append({"user_id": user.id, "error": str(exc)})

        return {
            "status": "success",
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "errors": errors,
        }
    finally:
        release_task_lock(LEGACY_ISSUE_SYNC_LOCK_NAME)
