"""Relay delivery strategy resolution helpers."""

from __future__ import annotations

from typing import Any, Dict, List

from relay.models import RelayDelivery, RelaySubscription
from threadline.utils.issues.merge_policy import is_retry_trigger_source

NEW = "new"
NEW_AND_LINK = "new_and_link"
UPDATE = "update"
SUPPORTED_ACTIONS = {NEW, NEW_AND_LINK, UPDATE}


def normalize_delivery_action(value: Any, *, default: str = NEW) -> str:
    normalized = str(value or default).strip().lower().replace("-", "_")
    if normalized in SUPPORTED_ACTIONS:
        return normalized
    if normalized in {"new_andlink", "newandlink"}:
        return NEW_AND_LINK
    return default


def _email_message_id(email_message) -> int | None:
    if email_message is None:
        return None

    value = getattr(email_message, "id", email_message)
    if value in (None, ""):
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _walk_email_cluster(email_message) -> list:
    if not email_message:
        return []

    stack = [email_message]
    visited: set[int] = set()
    cluster: list = []

    while stack:
        current = stack.pop()
        if not current or current.id in visited:
            continue
        visited.add(current.id)
        cluster.append(current)

        if getattr(current, "merged_into_id", None):
            stack.append(current.merged_into)

        merged_children = getattr(current, "merged_children", None)
        if merged_children is not None:
            for child in merged_children.all():
                stack.append(child)

    return cluster


def _latest_successful_delivery(subscription, email_message):
    email_message_id = _email_message_id(email_message)
    if email_message_id is None:
        return None

    return (
        RelayDelivery.objects.select_related("event", "subscription")
        .filter(
            subscription=subscription,
            status=RelayDelivery.Status.SUCCESS,
            event__email_message_id=email_message_id,
        )
        .exclude(external_id__isnull=True)
        .exclude(external_id="")
        .order_by("-created_at", "-id")
        .first()
    )


def _collect_related_issue_keys(subscription, email_message) -> list[str]:
    cluster = _walk_email_cluster(email_message)
    if not cluster:
        return []

    cluster_ids = [
        cluster_email_message_id
        for cluster_email_message_id in (
            _email_message_id(item) for item in cluster
        )
        if cluster_email_message_id is not None
    ]
    if not cluster_ids:
        return []

    deliveries = (
        RelayDelivery.objects.select_related("event", "subscription")
        .filter(
            subscription=subscription,
            status=RelayDelivery.Status.SUCCESS,
            event__email_message_id__in=cluster_ids,
        )
        .exclude(external_id__isnull=True)
        .exclude(external_id="")
        .order_by("created_at", "id")
    )

    related_issue_keys: list[str] = []
    for delivery in deliveries:
        if delivery.external_id and delivery.external_id not in related_issue_keys:
            related_issue_keys.append(delivery.external_id)
    return related_issue_keys


def _has_merge_context(email_message) -> bool:
    if not email_message:
        return False
    merged_children = getattr(email_message, "merged_children", None)
    has_children = bool(merged_children and merged_children.exists())
    return bool(getattr(email_message, "merged_into_id", None) or has_children)


def supports_linking(target_type: str) -> bool:
    return str(target_type or "").strip().lower() == RelaySubscription.TargetType.JIRA


def resolve_delivery_plan(subscription, event, delivery) -> Dict[str, Any]:
    """
    Resolve the effective delivery action for a Relay delivery.

    The explicit delivery_strategy wins. Otherwise, legacy strategy fields are
    combined into the three effective actions the UI describes:
    - new
    - new_and_link
    - update
    """

    strategies = subscription.strategies or {}
    explicit_action = normalize_delivery_action(
        strategies.get("delivery_strategy"), default=""
    )
    auto_action = normalize_delivery_action(
        strategies.get("auto_merge_strategy"), default=NEW
    )
    retry_action = normalize_delivery_action(
        strategies.get("retry_issue_strategy"), default=UPDATE
    )
    manual_strategy = str(
        strategies.get("manual_merge_strategy") or "linked"
    ).strip().lower()

    reference_delivery = _latest_successful_delivery(
        subscription, event.email_message
    )
    reference_external_id = delivery.external_id or (
        reference_delivery.external_id if reference_delivery else ""
    )
    related_issue_keys = _collect_related_issue_keys(
        subscription, event.email_message
    )
    has_merge_context = _has_merge_context(event.email_message)
    linking_supported = supports_linking(subscription.target_type)
    artifact_snapshot = getattr(event, "artifact_snapshot", None) or {}
    trigger_source = artifact_snapshot.get("trigger_source") or ""
    is_retry = bool(
        (getattr(delivery, "metadata", None) or {}).get("relay_retry_requested")
        or is_retry_trigger_source(trigger_source)
    )

    if explicit_action in SUPPORTED_ACTIONS:
        action = explicit_action
        source = "explicit"
    elif is_retry and reference_external_id and retry_action == UPDATE:
        action = UPDATE
        source = "retry"
    elif has_merge_context and manual_strategy == "linked" and related_issue_keys:
        action = NEW_AND_LINK
        source = "manual_merge"
    elif reference_external_id and auto_action == UPDATE:
        action = UPDATE
        source = "auto_merge"
    else:
        action = NEW
        source = "default"

    if action == UPDATE and not reference_external_id:
        action = NEW
        source = "fallback_new"

    if action == NEW_AND_LINK and not related_issue_keys:
        action = NEW
        source = "fallback_new_no_links"

    return {
        "action": action,
        "source": source,
        "reference_external_id": reference_external_id,
        "reference_delivery_id": reference_delivery.id if reference_delivery else None,
        "related_issue_keys": related_issue_keys,
        "linking_supported": linking_supported,
    }
