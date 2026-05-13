"""Relay strategy integration scenarios with DEVIFY TEST data."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from relay.models import RelayDelivery, RelayEvent, RelaySubscription
from relay.services.dispatcher import RelayDispatcher
from threadline.tests.fixtures.factories import EmailMessageFactory

from .helpers import build_real_jira_subscription_config, make_test_label


User = get_user_model()


pytestmark = [pytest.mark.django_db, pytest.mark.integration]


def _create_successful_delivery(*, event, subscription, external_id):
    return RelayDelivery.objects.create(
        event=event,
        subscription=subscription,
        target_type=subscription.target_type,
        status=RelayDelivery.Status.SUCCESS,
        external_id=external_id,
        external_url=f"https://jira.devify.test/browse/{external_id}",
        metadata={},
        idempotency_key=f"{event.id}:{subscription.id}:{external_id}",
    )


def _build_jira_subscription(*, user, name: str, strategies: dict) -> RelaySubscription:
    return RelaySubscription.objects.create(
        user=user,
        target_type=RelaySubscription.TargetType.JIRA,
        name=name,
        enabled=True,
        config=build_real_jira_subscription_config(),
        strategies=strategies,
        field_mappings={},
    )


def test_jira_strategy_default_creates_new_issue(monkeypatch):
    user = User.objects.create_user(
        username="devify-test-strategy-default",
        email="devify-test-strategy-default@example.com",
        password="secret",
    )
    email = EmailMessageFactory(
        user=user,
        subject=make_test_label("default", "summary"),
    )
    event = RelayEvent.objects.create(
        user=user,
        email_message=email,
        event_type=RelayEvent.EventType.WORKFLOW_COMPLETED,
        artifact_snapshot={
            "summary_title": make_test_label("default", "summary"),
            "summary_content": make_test_label("default", "description"),
            "llm_content": make_test_label("default", "description"),
            "trigger_source": "workflow",
        },
    )
    subscription = _build_jira_subscription(
        user=user,
        name=make_test_label("jira", "default", "channel"),
        strategies={
            "auto_merge_strategy": "new",
            "manual_merge_strategy": "unlinked",
            "retry_issue_strategy": "new",
        },
    )

    calls = {}

    def fake_create(self, **kwargs):
        calls["create"] = kwargs
        return "DEVIFY-TEST-NEW-1"

    monkeypatch.setattr(
        "relay.services.drivers.jira_handler.JiraIssueHandler.create_issue",
        fake_create,
    )
    monkeypatch.setattr(
        "relay.services.drivers.jira_handler.JiraIssueHandler.update_issue",
        lambda self, *args, **kwargs: pytest.fail("update_issue should not be called"),
    )
    monkeypatch.setattr(
        "relay.services.drivers.jira_handler.JiraIssueHandler.link_related_issues",
        lambda self, *args, **kwargs: pytest.fail("link_related_issues should not be called"),
    )
    monkeypatch.setattr(
        "relay.services.drivers.jira_handler.JiraIssueHandler.get_issue_url",
        lambda self, issue_key: f"https://jira.devify.test/browse/{issue_key}",
    )

    summary = RelayDispatcher.dispatch_event(event, task_id="task-devify-test-new")

    refreshed = RelayDelivery.objects.get(event=event, subscription=subscription)
    assert summary["success"] == 1
    assert refreshed.external_id == "DEVIFY-TEST-NEW-1"
    assert refreshed.metadata["relay_strategy"] == "new"
    assert refreshed.metadata["relay_strategy_source"] == "default"
    assert calls["create"]["issue_data"]["title"] == make_test_label("default", "summary")


def test_jira_strategy_auto_merge_updates_existing_issue(monkeypatch):
    user = User.objects.create_user(
        username="devify-test-strategy-auto",
        email="devify-test-strategy-auto@example.com",
        password="secret",
    )
    email = EmailMessageFactory(
        user=user,
        subject=make_test_label("auto", "summary"),
    )
    prior_event = RelayEvent.objects.create(
        user=user,
        email_message=email,
        event_type=RelayEvent.EventType.WORKFLOW_COMPLETED,
        artifact_snapshot={
            "summary_title": make_test_label("auto", "summary"),
            "summary_content": make_test_label("auto", "description"),
            "trigger_source": "workflow",
        },
        status=RelayEvent.Status.COMPLETED,
    )
    subscription = _build_jira_subscription(
        user=user,
        name=make_test_label("jira", "auto", "update", "channel"),
        strategies={
            "auto_merge_strategy": "update",
            "manual_merge_strategy": "unlinked",
            "retry_issue_strategy": "new",
        },
    )
    _create_successful_delivery(
        event=prior_event,
        subscription=subscription,
        external_id="DEVIFY-TEST-REQ-123",
    )
    event = RelayEvent.objects.create(
        user=user,
        email_message=email,
        event_type=RelayEvent.EventType.WORKFLOW_COMPLETED,
        artifact_snapshot={
            "summary_title": make_test_label("auto", "updated", "summary"),
            "summary_content": make_test_label("auto", "updated", "description"),
            "trigger_source": "workflow",
        },
    )

    calls = {}

    def fake_update(self, issue_key, **kwargs):
        calls["update"] = {"issue_key": issue_key, **kwargs}
        return issue_key

    monkeypatch.setattr(
        "relay.services.drivers.jira_handler.JiraIssueHandler.update_issue",
        fake_update,
    )
    monkeypatch.setattr(
        "relay.services.drivers.jira_handler.JiraIssueHandler.create_issue",
        lambda self, **kwargs: pytest.fail("create_issue should not be called"),
    )
    monkeypatch.setattr(
        "relay.services.drivers.jira_handler.JiraIssueHandler.get_issue_url",
        lambda self, issue_key: f"https://jira.devify.test/browse/{issue_key}",
    )

    summary = RelayDispatcher.dispatch_event(event, task_id="task-devify-test-auto")

    refreshed = RelayDelivery.objects.get(event=event, subscription=subscription)
    assert summary["success"] == 1
    assert refreshed.external_id == "DEVIFY-TEST-REQ-123"
    assert refreshed.metadata["relay_strategy"] == "update"
    assert refreshed.metadata["relay_strategy_source"] == "auto_merge"
    assert calls["update"]["issue_key"] == "DEVIFY-TEST-REQ-123"
    assert calls["update"]["issue_data"]["title"] == make_test_label("auto", "updated", "summary")


def test_jira_strategy_manual_merge_creates_and_links(monkeypatch):
    user = User.objects.create_user(
        username="devify-test-strategy-manual",
        email="devify-test-strategy-manual@example.com",
        password="secret",
    )
    parent_email = EmailMessageFactory(
        user=user,
        subject=make_test_label("manual", "parent", "summary"),
    )
    child_email = EmailMessageFactory(
        user=user,
        subject=make_test_label("manual", "child", "summary"),
    )
    child_email.merged_into = parent_email
    child_email.save(update_fields=["merged_into"])

    parent_event = RelayEvent.objects.create(
        user=user,
        email_message=parent_email,
        event_type=RelayEvent.EventType.WORKFLOW_COMPLETED,
        artifact_snapshot={
            "summary_title": make_test_label("manual", "parent", "summary"),
            "summary_content": make_test_label("manual", "parent", "description"),
            "trigger_source": "workflow",
        },
        status=RelayEvent.Status.COMPLETED,
    )
    event = RelayEvent.objects.create(
        user=user,
        email_message=child_email,
        event_type=RelayEvent.EventType.WORKFLOW_COMPLETED,
        artifact_snapshot={
            "summary_title": make_test_label("manual", "child", "summary"),
            "summary_content": make_test_label("manual", "child", "description"),
            "trigger_source": "workflow",
        },
    )
    subscription = _build_jira_subscription(
        user=user,
        name=make_test_label("jira", "manual", "link", "channel"),
        strategies={
            "auto_merge_strategy": "new",
            "manual_merge_strategy": "linked",
            "retry_issue_strategy": "new",
        },
    )
    _create_successful_delivery(
        event=parent_event,
        subscription=subscription,
        external_id="DEVIFY-TEST-REQ-111",
    )

    calls = {}

    def fake_create(self, **kwargs):
        calls["create"] = kwargs
        return "DEVIFY-TEST-REQ-222"

    def fake_link(self, issue_key, related_issue_keys, *, link_type="Relates"):
        calls["link"] = {
            "issue_key": issue_key,
            "related_issue_keys": list(related_issue_keys),
            "link_type": link_type,
        }
        return {"linked_count": len(related_issue_keys), "skipped_count": 0}

    monkeypatch.setattr(
        "relay.services.drivers.jira_handler.JiraIssueHandler.create_issue",
        fake_create,
    )
    monkeypatch.setattr(
        "relay.services.drivers.jira_handler.JiraIssueHandler.link_related_issues",
        fake_link,
    )
    monkeypatch.setattr(
        "relay.services.drivers.jira_handler.JiraIssueHandler.get_issue_url",
        lambda self, issue_key: f"https://jira.devify.test/browse/{issue_key}",
    )

    summary = RelayDispatcher.dispatch_event(event, task_id="task-devify-test-manual")

    refreshed = RelayDelivery.objects.get(event=event, subscription=subscription)
    assert summary["success"] == 1
    assert refreshed.external_id == "DEVIFY-TEST-REQ-222"
    assert refreshed.metadata["relay_strategy"] == "new_and_link"
    assert refreshed.metadata["relay_strategy_source"] == "manual_merge"
    assert calls["create"]["issue_data"]["title"] == make_test_label("manual", "child", "summary")
    assert calls["link"]["issue_key"] == "DEVIFY-TEST-REQ-222"
    assert calls["link"]["related_issue_keys"] == ["DEVIFY-TEST-REQ-111"]


def test_jira_strategy_retry_updates_existing_issue(monkeypatch):
    user = User.objects.create_user(
        username="devify-test-strategy-retry",
        email="devify-test-strategy-retry@example.com",
        password="secret",
    )
    email = EmailMessageFactory(
        user=user,
        subject=make_test_label("retry", "summary"),
    )
    event = RelayEvent.objects.create(
        user=user,
        email_message=email,
        event_type=RelayEvent.EventType.WORKFLOW_COMPLETED,
        artifact_snapshot={
            "summary_title": make_test_label("retry", "summary"),
            "summary_content": make_test_label("retry", "description"),
            "trigger_source": "workflow",
        },
        status=RelayEvent.Status.FAILED,
    )
    subscription = _build_jira_subscription(
        user=user,
        name=make_test_label("jira", "retry", "update", "channel"),
        strategies={
            "auto_merge_strategy": "new",
            "manual_merge_strategy": "unlinked",
            "retry_issue_strategy": "update",
        },
    )
    delivery = RelayDelivery.objects.create(
        event=event,
        subscription=subscription,
        target_type=subscription.target_type,
        status=RelayDelivery.Status.FAILED,
        external_id="DEVIFY-TEST-REQ-555",
        external_url="https://jira.devify.test/browse/DEVIFY-TEST-REQ-555",
        error_message="boom",
        metadata={},
        idempotency_key="devify-test-retry-555",
    )

    calls = {}

    def fake_update(self, issue_key, **kwargs):
        calls["update"] = {"issue_key": issue_key, **kwargs}
        return issue_key

    monkeypatch.setattr(
        "relay.services.drivers.jira_handler.JiraIssueHandler.update_issue",
        fake_update,
    )
    monkeypatch.setattr(
        "relay.services.drivers.jira_handler.JiraIssueHandler.create_issue",
        lambda self, **kwargs: pytest.fail("create_issue should not be called"),
    )
    monkeypatch.setattr(
        "relay.services.drivers.jira_handler.JiraIssueHandler.get_issue_url",
        lambda self, issue_key: f"https://jira.devify.test/browse/{issue_key}",
    )

    summary = RelayDispatcher.retry_delivery(delivery, task_id="task-devify-test-retry")

    refreshed = RelayDelivery.objects.get(id=delivery.id)
    assert summary["success"] == 1
    assert refreshed.status == RelayDelivery.Status.SUCCESS
    assert refreshed.external_id == "DEVIFY-TEST-REQ-555"
    assert refreshed.metadata["relay_strategy"] == "update"
    assert refreshed.metadata["relay_strategy_source"] == "retry"
    assert calls["update"]["issue_key"] == "DEVIFY-TEST-REQ-555"
    assert calls["update"]["issue_data"]["title"] == make_test_label("retry", "summary")
