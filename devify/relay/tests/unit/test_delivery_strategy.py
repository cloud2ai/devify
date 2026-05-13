"""Relay delivery strategy unit tests."""

from __future__ import annotations

from types import SimpleNamespace

from relay.models import RelaySubscription
from relay.services.delivery_strategy import resolve_delivery_plan


def _make_subscription(
    *,
    target_type: str = RelaySubscription.TargetType.JIRA,
    strategies: dict | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        target_type=target_type,
        strategies=strategies or {},
    )


def _make_event(*, merged_into_id=None, trigger_source="workflow") -> SimpleNamespace:
    return SimpleNamespace(
        email_message=SimpleNamespace(
            id=101,
            merged_into_id=merged_into_id,
        ),
        email_message_id=101,
        artifact_snapshot={"trigger_source": trigger_source},
    )


def _make_delivery(*, external_id="", metadata=None) -> SimpleNamespace:
    return SimpleNamespace(
        external_id=external_id,
        metadata=metadata or {},
    )


def test_auto_merge_strategy_update_resolves_to_update(monkeypatch):
    subscription = _make_subscription(
        strategies={
            "auto_merge_strategy": "update",
            "manual_merge_strategy": "unlinked",
            "retry_issue_strategy": "new",
        }
    )
    event = _make_event()
    delivery = _make_delivery()

    monkeypatch.setattr(
        "relay.services.delivery_strategy._latest_successful_delivery",
        lambda subscription, email_message: SimpleNamespace(
            id=7,
            external_id="REQ-123",
        ),
    )
    monkeypatch.setattr(
        "relay.services.delivery_strategy._collect_related_issue_keys",
        lambda subscription, email_message: [],
    )
    monkeypatch.setattr(
        "relay.services.delivery_strategy._has_merge_context",
        lambda email_message: False,
    )

    plan = resolve_delivery_plan(subscription, event, delivery)

    assert plan["action"] == "update"
    assert plan["source"] == "auto_merge"
    assert plan["reference_external_id"] == "REQ-123"
    assert plan["related_issue_keys"] == []


def test_manual_merge_strategy_linked_resolves_to_new_and_link(monkeypatch):
    subscription = _make_subscription(
        strategies={
            "auto_merge_strategy": "new",
            "manual_merge_strategy": "linked",
            "retry_issue_strategy": "new",
        }
    )
    event = _make_event(merged_into_id=1)
    delivery = _make_delivery()

    monkeypatch.setattr(
        "relay.services.delivery_strategy._latest_successful_delivery",
        lambda subscription, email_message: None,
    )
    monkeypatch.setattr(
        "relay.services.delivery_strategy._collect_related_issue_keys",
        lambda subscription, email_message: ["REQ-111"],
    )
    monkeypatch.setattr(
        "relay.services.delivery_strategy._has_merge_context",
        lambda email_message: True,
    )

    plan = resolve_delivery_plan(subscription, event, delivery)

    assert plan["action"] == "new_and_link"
    assert plan["source"] == "manual_merge"
    assert plan["reference_external_id"] == ""
    assert plan["related_issue_keys"] == ["REQ-111"]


def test_default_strategy_resolves_to_new(monkeypatch):
    subscription = _make_subscription(
        strategies={
            "auto_merge_strategy": "new",
            "manual_merge_strategy": "unlinked",
            "retry_issue_strategy": "new",
        }
    )
    event = _make_event()
    delivery = _make_delivery()

    monkeypatch.setattr(
        "relay.services.delivery_strategy._latest_successful_delivery",
        lambda subscription, email_message: None,
    )
    monkeypatch.setattr(
        "relay.services.delivery_strategy._collect_related_issue_keys",
        lambda subscription, email_message: [],
    )
    monkeypatch.setattr(
        "relay.services.delivery_strategy._has_merge_context",
        lambda email_message: False,
    )

    plan = resolve_delivery_plan(subscription, event, delivery)

    assert plan["action"] == "new"
    assert plan["source"] == "default"
    assert plan["reference_external_id"] == ""
    assert plan["related_issue_keys"] == []


def test_retry_strategy_update_resolves_to_update(monkeypatch):
    subscription = _make_subscription(
        strategies={
            "auto_merge_strategy": "new",
            "manual_merge_strategy": "unlinked",
            "retry_issue_strategy": "update",
        }
    )
    event = _make_event(trigger_source="retry")
    delivery = _make_delivery(
        external_id="REQ-555",
        metadata={"relay_retry_requested": True},
    )

    monkeypatch.setattr(
        "relay.services.delivery_strategy._latest_successful_delivery",
        lambda subscription, email_message: SimpleNamespace(
            id=9,
            external_id="REQ-555",
        ),
    )
    monkeypatch.setattr(
        "relay.services.delivery_strategy._collect_related_issue_keys",
        lambda subscription, email_message: [],
    )
    monkeypatch.setattr(
        "relay.services.delivery_strategy._has_merge_context",
        lambda email_message: False,
    )

    plan = resolve_delivery_plan(subscription, event, delivery)

    assert plan["action"] == "update"
    assert plan["source"] == "retry"
    assert plan["reference_external_id"] == "REQ-555"
    assert plan["related_issue_keys"] == []
