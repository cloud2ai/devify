from __future__ import annotations

import os
from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from agentcore_task.adapters.django.models import TaskExecution
from relay.models import RelayDelivery, RelayEvent, RelaySubscription
from relay.services.dispatcher import RelayDispatcher
from relay.services.publisher import RelayEventPublisher
from relay.services.test_attachments import (
    BUILTIN_TEST_ATTACHMENT,
    build_test_attachments,
)
from relay.tasks import process_relay_delivery
from threadline.agents.nodes.workflow_finalize import WorkflowFinalizeNode
from threadline.models import EmailMessage
from threadline.tests.fixtures.factories import EmailMessageFactory


User = get_user_model()


class _TestAdapter:
    def __init__(self):
        self.calls = 0

    def deliver(self, *, event, subscription, delivery):
        self.calls += 1
        return SimpleNamespace(
            external_id=f"ext-{subscription.id}",
            external_url=f"https://example.com/{subscription.id}",
            metadata={"adapter": subscription.target_type},
        )


def _create_successful_delivery(*, event, subscription, external_id, external_url):
    return RelayDelivery.objects.create(
        event=event,
        subscription=subscription,
        target_type=subscription.target_type,
        status=RelayDelivery.Status.SUCCESS,
        external_id=external_id,
        external_url=external_url,
        metadata={},
        idempotency_key=f"{event.id}:{subscription.id}:{external_id}",
    )


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_workflow_finalize_publishes_relay_event(monkeypatch):
    user = User.objects.create_user(
        username="relay-user",
        email="relay@example.com",
        password="secret",
    )
    email = EmailMessageFactory(user=user)
    email.status = "processing"
    email.save(update_fields=["status"])
    called = {}

    def fake_publish(*, email, state):
        called["email_id"] = email.id
        called["state"] = state
        return SimpleNamespace(id=123)

    monkeypatch.setattr(
        "relay.services.publisher.RelayEventPublisher.publish_workflow_completed",
        fake_publish,
    )
    monkeypatch.setattr(
        WorkflowFinalizeNode,
        "_record_usage_metrics",
        lambda self, email, state: None,
    )

    node = WorkflowFinalizeNode()
    node.email = email
    node.execute_processing(
        {
            "id": email.id,
            "user_id": user.id,
            "summary_title": "Relay summary",
            "summary_content": "Relay content",
            "llm_content": "Relay content",
            "metadata": {"source": "test"},
        }
    )

    assert called["email_id"] == email.id
    assert called["state"]["summary_title"] == "Relay summary"


def test_relay_event_snapshot_preserves_attachments():
    snapshot = RelayEventPublisher._build_snapshot(
        {
            "id": 11,
            "user_id": 22,
            "summary_title": "Attachment title",
            "attachments": [
                {
                    "id": "att-1",
                    "filename": "demo.pdf",
                    "safe_filename": "demo.pdf",
                    "file_path": "/tmp/demo.pdf",
                }
            ],
        }
    )

    assert snapshot["attachment_count"] == 1
    assert snapshot["attachments"][0]["file_path"] == "/tmp/demo.pdf"


def test_relay_test_attachments_fall_back_to_builtin_sample():
    attachments, temp_paths = build_test_attachments(None)

    assert len(attachments) == 0
    assert temp_paths == []

    builtin_attachments, builtin_temp_paths = build_test_attachments(
        [BUILTIN_TEST_ATTACHMENT]
    )

    assert len(builtin_attachments) == 1
    assert builtin_attachments[0]["filename"] == "builtin-test-image.png"
    assert builtin_attachments[0]["content_type"] == "image/png"
    assert len(builtin_temp_paths) == 1

    for path in builtin_temp_paths:
        if path and os.path.exists(path):
            os.remove(path)


@pytest.mark.django_db
def test_relay_test_endpoint_uses_subscription_configuration(api_client, monkeypatch):
    user = User.objects.create_user(
        username="relay-user-test-endpoint",
        email="relay-test-endpoint@example.com",
        password="secret",
    )
    subscription = RelaySubscription.objects.create(
        user=user,
        target_type=RelaySubscription.TargetType.FEISHU_BITABLE,
        name="feishu-test",
        enabled=True,
        config={
            "issue_engine": "feishu_bitable",
            "feishu_bitable": {
                "app_id": "cli_xxx",
                "app_secret": "secret",
                "app_token_type": "bitable",
                "app_token": "app-token",
                "table_name": "Issue Table",
                "attachment_field_name": "附件",
                "field_mappings": {
                    "任务简述": "title",
                },
            },
        },
        strategies={},
        field_mappings={"任务简述": "title"},
    )
    captured = {}

    class _TestRelayAdapter:
        def deliver(self, *, event, subscription, delivery):
            captured["subscription_config"] = subscription.config
            captured["event_subject"] = event.email_message.subject
            captured["delivery_metadata"] = delivery.metadata
            captured["attachments"] = event.artifact_snapshot["attachments"]
            return SimpleNamespace(
                external_id="record-1",
                external_url="https://example.com/record-1",
                metadata={"adapter": subscription.target_type},
            )

    monkeypatch.setattr(
        "relay.services.adapters.RelayAdapterRegistry.get_adapter",
        lambda target_type: _TestRelayAdapter(),
    )

    api_client.force_authenticate(user=user)
    response = api_client.post(
        reverse("relay-test"),
        {
            "subscription_id": subscription.id,
            "artifact_snapshot": {
                "summary_title": "devify test summary",
                "summary_content": "devify test description",
                "llm_content": "devify test description",
            },
        },
        format="json",
    )

    assert response.status_code == 200
    assert response.data["data"]["external_id"] == "record-1"
    assert captured["subscription_config"]["feishu_bitable"]["app_id"] == "cli_xxx"
    assert captured["event_subject"] == "devify test summary"
    assert captured["delivery_metadata"]["relay_delivery_plan"]["action"] == "new"
    assert captured["attachments"][0]["filename"] == "builtin-test-image.png"
    assert captured["attachments"][0]["content_type"] == "image/png"


@pytest.mark.django_db
def test_relay_test_endpoint_returns_400_when_delivery_fails(api_client, monkeypatch):
    user = User.objects.create_user(
        username="relay-user-test-endpoint-fail",
        email="relay-test-endpoint-fail@example.com",
        password="secret",
    )
    subscription = RelaySubscription.objects.create(
        user=user,
        target_type=RelaySubscription.TargetType.FEISHU_BITABLE,
        name="feishu-test-fail",
        enabled=True,
        config={
            "issue_engine": "feishu_bitable",
            "feishu_bitable": {
                "app_id": "cli_xxx",
                "app_secret": "secret",
                "app_token_type": "bitable",
                "app_token": "app-token",
                "table_name": "Issue Table",
                "attachment_field_name": "附件",
                "field_mappings": {
                    "任务简述": "title",
                },
            },
        },
        strategies={},
        field_mappings={"任务简述": "title"},
    )

    class _FailingRelayAdapter:
        def deliver(self, *, event, subscription, delivery):
            raise ValueError("Feishu attachment upload failed for field 附件")

    monkeypatch.setattr(
        "relay.services.adapters.RelayAdapterRegistry.get_adapter",
        lambda target_type: _FailingRelayAdapter(),
    )

    api_client.force_authenticate(user=user)
    response = api_client.post(
        reverse("relay-test"),
        {
            "subscription_id": subscription.id,
            "artifact_snapshot": {
                "summary_title": "devify test summary",
                "summary_content": "devify test description",
                "llm_content": "devify test description",
            },
        },
        format="json",
    )

    assert response.status_code == 400
    assert "attachment upload failed" in response.data["message"].lower()


@pytest.mark.django_db
def test_relay_test_endpoint_accepts_draft_subscription_config(api_client, monkeypatch):
    user = User.objects.create_user(
        username="relay-user-draft-config",
        email="relay-draft-config@example.com",
        password="secret",
    )
    captured = {}

    class _TestRelayAdapter:
        def deliver(self, *, event, subscription, delivery):
            captured["subscription_config"] = subscription.config
            captured["subscription_target_type"] = subscription.target_type
            captured["delivery_plan"] = delivery.metadata.get("relay_delivery_plan")
            return SimpleNamespace(
                external_id="record-draft-1",
                external_url="https://example.com/record-draft-1",
                metadata={"adapter": subscription.target_type},
            )

    monkeypatch.setattr(
        "relay.services.adapters.RelayAdapterRegistry.get_adapter",
        lambda target_type: _TestRelayAdapter(),
    )

    api_client.force_authenticate(user=user)
    response = api_client.post(
        reverse("relay-test"),
        {
            "target_type": "feishu_bitable",
            "subscription": {
                "target_type": "feishu_bitable",
                "config": {
                    "issue_engine": "feishu_bitable",
                    "enable": True,
                    "feishu_bitable": {
                        "app_id": "cli_xxx",
                        "app_secret": "secret",
                        "app_token_type": "wiki",
                        "app_token": "wiki-node-token",
                        "table_name": "Issue Table",
                        "attachment_field_name": "附件",
                        "field_mappings": {
                            "任务简述": "title",
                        },
                    },
                },
                "strategies": {
                    "auto_merge_strategy": "new",
                    "manual_merge_strategy": "linked",
                    "retry_issue_strategy": "update",
                },
                "field_mappings": {"任务简述": "title"},
            },
            "artifact_snapshot": {
                "summary_title": "draft summary",
                "summary_content": "draft body",
                "llm_content": "draft body",
            },
        },
        format="json",
    )

    assert response.status_code == 200
    assert response.data["data"]["external_id"] == "record-draft-1"
    assert captured["subscription_target_type"] == "feishu_bitable"
    assert captured["subscription_config"]["feishu_bitable"]["app_token_type"] == "wiki"
    assert captured["subscription_config"]["feishu_bitable"]["app_token"] == "wiki-node-token"
    assert captured["delivery_plan"]["action"] == "new"


@pytest.mark.django_db
def test_relay_test_endpoint_merges_draft_over_existing_subscription(
    api_client, monkeypatch
):
    user = User.objects.create_user(
        username="relay-user-draft-merge",
        email="relay-draft-merge@example.com",
        password="secret",
    )
    subscription = RelaySubscription.objects.create(
        user=user,
        name="Existing subscription",
        target_type="feishu_bitable",
        enabled=True,
        config={
            "issue_engine": "feishu_bitable",
            "enable": True,
            "feishu_bitable": {
                "app_token_type": "bitable",
                "app_token": "bascn-old-token",
                "table_name": "Issue Table",
                "attachment_field_name": "附件",
            },
        },
        strategies={"auto_merge_strategy": "new"},
        field_mappings={"任务简述": "title"},
    )
    captured = {}

    class _TestRelayAdapter:
        def deliver(self, *, event, subscription, delivery):
            captured["subscription_config"] = subscription.config
            captured["subscription_target_type"] = subscription.target_type
            return SimpleNamespace(
                external_id="record-merge-1",
                external_url="https://example.com/record-merge-1",
                metadata={"adapter": subscription.target_type},
            )

    monkeypatch.setattr(
        "relay.services.adapters.RelayAdapterRegistry.get_adapter",
        lambda target_type: _TestRelayAdapter(),
    )

    api_client.force_authenticate(user=user)
    response = api_client.post(
        reverse("relay-test"),
        {
            "subscription_id": subscription.id,
            "subscription": {
                "target_type": "feishu_bitable",
                "config": {
                    "issue_engine": "feishu_bitable",
                    "enable": True,
                    "feishu_bitable": {
                        "app_token_type": "wiki",
                        "app_token": "wiki-node-token",
                        "table_name": "Issue Table",
                        "attachment_field_name": "附件",
                        "field_mappings": {"任务简述": "title"},
                    },
                },
                "strategies": {
                    "auto_merge_strategy": "new",
                    "manual_merge_strategy": "linked",
                    "retry_issue_strategy": "update",
                },
                "field_mappings": {"任务简述": "title"},
            },
            "artifact_snapshot": {
                "summary_title": "draft summary",
                "summary_content": "draft body",
                "llm_content": "draft body",
            },
        },
        format="json",
    )

    assert response.status_code == 200
    assert response.data["data"]["external_id"] == "record-merge-1"
    assert captured["subscription_target_type"] == "feishu_bitable"
    assert captured["subscription_config"]["feishu_bitable"]["app_token_type"] == "wiki"
    assert captured["subscription_config"]["feishu_bitable"]["app_token"] == "wiki-node-token"


@pytest.mark.django_db
def test_relay_event_list_exposes_canonical_email_root(api_client):
    user = User.objects.create_user(
        username="relay-user-root",
        email="relay-root@example.com",
        password="secret",
    )
    parent_email = EmailMessageFactory(user=user)
    child_email = EmailMessageFactory(user=user)
    child_email.merged_into = parent_email
    child_email.save(update_fields=["merged_into"])

    RelayEvent.objects.create(
        user=user,
        email_message=parent_email,
        event_type=RelayEvent.EventType.WORKFLOW_COMPLETED,
        artifact_snapshot={"summary_title": "Parent title"},
    )
    RelayEvent.objects.create(
        user=user,
        email_message=child_email,
        event_type=RelayEvent.EventType.WORKFLOW_COMPLETED,
        artifact_snapshot={"summary_title": "Child title"},
    )

    api_client.force_authenticate(user=user)
    response = api_client.get(reverse("relay-events"))

    assert response.status_code == 200
    items = response.data["data"]["items"]
    assert len(items) == 2
    assert items[0]["email_message_root_uuid"] == str(parent_email.uuid)
    assert items[1]["email_message_root_uuid"] == str(parent_email.uuid)
    assert items[0]["email_message_uuid"] != items[1]["email_message_uuid"]
    assert items[0]["email_message_merged_into_uuid"] == str(parent_email.uuid)


@pytest.mark.django_db
def test_relay_dispatcher_creates_only_enabled_deliveries(monkeypatch):
    user = User.objects.create_user(
        username="relay-user-2",
        email="relay2@example.com",
        password="secret",
    )
    email = EmailMessageFactory(user=user)
    event = RelayEvent.objects.create(
        user=user,
        email_message=email,
        event_type=RelayEvent.EventType.WORKFLOW_COMPLETED,
        artifact_snapshot={
            "summary_title": "Test title",
            "summary_content": "Test content",
        },
    )
    enabled = RelaySubscription.objects.create(
        user=user,
        target_type=RelaySubscription.TargetType.JIRA,
        name="jira-main",
        enabled=True,
        config={"jira": {"url": "https://jira.example.com"}},
        strategies={"retry_issue_strategy": "update"},
        field_mappings={},
    )
    RelaySubscription.objects.create(
        user=user,
        target_type=RelaySubscription.TargetType.FEISHU_BITABLE,
        name="feishu-disabled",
        enabled=False,
        config={"feishu_bitable": {"app_token": "abc"}},
        strategies={},
        field_mappings={},
    )
    test_adapter = _TestAdapter()
    monkeypatch.setattr(
        "relay.services.adapters.RelayAdapterRegistry.get_adapter",
        lambda target_type: test_adapter,
    )

    summary = RelayDispatcher.dispatch_event(event, task_id="task-123")

    assert summary["success"] == 1
    assert summary["failed"] == 0
    assert RelayDelivery.objects.filter(event=event).count() == 1
    delivery = RelayDelivery.objects.get(event=event, subscription=enabled)
    assert delivery.status == RelayDelivery.Status.SUCCESS
    assert delivery.external_id == f"ext-{enabled.id}"
    assert delivery.agentcore_task_id == "task-123"
    assert test_adapter.calls == 1
    assert RelayEvent.objects.get(id=event.id).status == RelayEvent.Status.COMPLETED


@pytest.mark.django_db
def test_relay_dispatcher_retries_single_delivery(monkeypatch):
    user = User.objects.create_user(
        username="relay-user-3",
        email="relay3@example.com",
        password="secret",
    )
    email = EmailMessageFactory(user=user)
    event = RelayEvent.objects.create(
        user=user,
        email_message=email,
        event_type=RelayEvent.EventType.WORKFLOW_COMPLETED,
        artifact_snapshot={
            "summary_title": "Retry title",
            "summary_content": "Retry content",
        },
        status=RelayEvent.Status.FAILED,
    )
    subscription = RelaySubscription.objects.create(
        user=user,
        target_type=RelaySubscription.TargetType.JIRA,
        name="jira-retry",
        enabled=True,
        config={"jira": {"url": "https://jira.example.com"}},
        strategies={"retry_issue_strategy": "update"},
        field_mappings={},
    )
    delivery = RelayDelivery.objects.create(
        event=event,
        subscription=subscription,
        target_type=subscription.target_type,
        status=RelayDelivery.Status.FAILED,
        external_id="REQ-123",
        external_url="https://jira.example.com/browse/REQ-123",
        error_message="previous failure",
        metadata={},
        idempotency_key="retry-1",
    )
    test_adapter = _TestAdapter()
    monkeypatch.setattr(
        "relay.services.adapters.RelayAdapterRegistry.get_adapter",
        lambda target_type: test_adapter,
    )

    summary = RelayDispatcher.retry_delivery(delivery, task_id="task-456")

    assert summary["success"] == 1
    assert test_adapter.calls == 1
    refreshed = RelayDelivery.objects.get(id=delivery.id)
    assert refreshed.status == RelayDelivery.Status.SUCCESS
    assert refreshed.agentcore_task_id == "task-456"
    assert refreshed.external_id == f"ext-{subscription.id}"
    assert RelayEvent.objects.get(id=event.id).status == RelayEvent.Status.COMPLETED


@pytest.mark.django_db
def test_relay_dispatcher_updates_existing_issue_when_auto_merge_wants_update(
    monkeypatch,
):
    user = User.objects.create_user(
        username="relay-user-merge-update",
        email="relay-merge-update@example.com",
        password="secret",
    )
    email = EmailMessageFactory(user=user)
    prior_event = RelayEvent.objects.create(
        user=user,
        email_message=email,
        event_type=RelayEvent.EventType.WORKFLOW_COMPLETED,
        artifact_snapshot={
            "summary_title": "Prior title",
            "summary_content": "Prior content",
        },
        status=RelayEvent.Status.COMPLETED,
    )
    subscription = RelaySubscription.objects.create(
        user=user,
        target_type=RelaySubscription.TargetType.JIRA,
        name="jira-auto-update",
        enabled=True,
        config={"jira": {"url": "https://jira.example.com"}},
        strategies={"auto_merge_strategy": "update"},
        field_mappings={},
    )
    _create_successful_delivery(
        event=prior_event,
        subscription=subscription,
        external_id="REQ-123",
        external_url="https://jira.example.com/browse/REQ-123",
    )

    event = RelayEvent.objects.create(
        user=user,
        email_message=email,
        event_type=RelayEvent.EventType.WORKFLOW_COMPLETED,
        artifact_snapshot={
            "summary_title": "Updated title",
            "summary_content": "Updated content",
        },
    )

    monkeypatch.setattr(
        "relay.services.drivers.jira_handler.JiraIssueHandler.update_issue",
        lambda self, issue_key, **kwargs: issue_key,
    )
    monkeypatch.setattr(
        "relay.services.drivers.jira_handler.JiraIssueHandler.create_issue",
        lambda self, **kwargs: pytest.fail("create_issue should not be called"),
    )
    monkeypatch.setattr(
        "relay.services.drivers.jira_handler.JiraIssueHandler.get_issue_url",
        lambda self, issue_key: f"https://jira.example.com/browse/{issue_key}",
    )

    summary = RelayDispatcher.dispatch_event(event, task_id="task-auto-update")

    refreshed = RelayDelivery.objects.get(event=event, subscription=subscription)
    assert summary["success"] == 1
    assert refreshed.external_id == "REQ-123"
    assert refreshed.metadata["relay_strategy"] == "update"


@pytest.mark.django_db
def test_relay_retry_uploads_jira_attachments(monkeypatch):
    user = User.objects.create_user(
        username="relay-user-jira-attachments",
        email="relay-jira-attachments@example.com",
        password="secret",
    )
    email = EmailMessageFactory(user=user)
    event = RelayEvent.objects.create(
        user=user,
        email_message=email,
        event_type=RelayEvent.EventType.WORKFLOW_COMPLETED,
        artifact_snapshot={
            "summary_title": "Attachment retry title",
            "summary_content": "Attachment retry content",
            "attachments": [
                {
                    "id": "att-1",
                    "filename": "demo.png",
                    "safe_filename": "demo.png",
                    "content_md5": "md5-1",
                    "content_type": "image/png",
                    "file_size": 12,
                    "file_path": "/tmp/demo.png",
                    "is_image": True,
                }
            ],
        },
        status=RelayEvent.Status.FAILED,
    )
    subscription = RelaySubscription.objects.create(
        user=user,
        target_type=RelaySubscription.TargetType.JIRA,
        name="jira-attachment-retry",
        enabled=True,
        config={"jira": {"url": "https://jira.example.com"}},
        strategies={"retry_issue_strategy": "update"},
        field_mappings={},
    )
    delivery = RelayDelivery.objects.create(
        event=event,
        subscription=subscription,
        target_type=subscription.target_type,
        status=RelayDelivery.Status.FAILED,
        external_id="REQ-555",
        external_url="https://jira.example.com/browse/REQ-555",
        error_message="boom",
        metadata={},
        idempotency_key="retry-attachments-1",
    )

    def fake_update(self, issue_key, **kwargs):
        return issue_key

    upload_calls = {}

    def fake_upload(self, issue_key, attachments):
        upload_calls["issue_key"] = issue_key
        upload_calls["attachments"] = list(attachments)
        return {
            "uploaded_count": len(attachments),
            "skipped_count": 0,
            "uploaded_attachment_keys": [
                "md5:md5-1",
                "id:att-1",
                "name:demo.png:12",
            ],
            "skipped_attachment_keys": [],
        }

    monkeypatch.setattr(
        "relay.services.drivers.jira_handler.JiraIssueHandler.update_issue",
        fake_update,
    )
    monkeypatch.setattr(
        "relay.services.drivers.jira_handler.JiraIssueHandler.upload_attachments",
        fake_upload,
    )
    monkeypatch.setattr(
        "relay.services.drivers.jira_handler.JiraIssueHandler.get_issue_url",
        lambda self, issue_key: f"https://jira.example.com/browse/{issue_key}",
    )
    monkeypatch.setattr(
        "relay.services.drivers.jira_handler.JiraIssueHandler.get_issue_attachment_fingerprints",
        lambda self, issue_key: [],
    )

    summary = RelayDispatcher.retry_delivery(delivery, task_id="task-attachments")

    refreshed = RelayDelivery.objects.get(id=delivery.id)
    assert summary["success"] == 1
    assert refreshed.external_id == "REQ-555"
    assert refreshed.metadata["relay_strategy"] == "update"
    assert refreshed.metadata["upload_result"]["uploaded_count"] == 1
    assert refreshed.metadata["uploaded_attachment_keys"] == [
        "md5:md5-1",
        "id:att-1",
        "name:demo.png:12",
    ]
    assert upload_calls["issue_key"] == "REQ-555"
    assert len(upload_calls["attachments"]) == 1


@pytest.mark.django_db
def test_relay_retry_preserves_existing_uploaded_attachment_keys(monkeypatch):
    user = User.objects.create_user(
        username="relay-user-jira-attachment-skip",
        email="relay-jira-attachment-skip@example.com",
        password="secret",
    )
    email = EmailMessageFactory(user=user)
    event = RelayEvent.objects.create(
        user=user,
        email_message=email,
        event_type=RelayEvent.EventType.WORKFLOW_COMPLETED,
        artifact_snapshot={
            "summary_title": "Attachment skip title",
            "summary_content": "Attachment skip content",
            "attachments": [
                {
                    "id": "att-1",
                    "filename": "demo.png",
                    "safe_filename": "demo.png",
                    "content_md5": "md5-1",
                    "content_type": "image/png",
                    "file_size": 12,
                    "file_path": "/tmp/demo.png",
                    "is_image": True,
                }
            ],
        },
        status=RelayEvent.Status.FAILED,
    )
    subscription = RelaySubscription.objects.create(
        user=user,
        target_type=RelaySubscription.TargetType.JIRA,
        name="jira-attachment-skip",
        enabled=True,
        config={"jira": {"url": "https://jira.example.com"}},
        strategies={"retry_issue_strategy": "update"},
        field_mappings={},
    )
    delivery = RelayDelivery.objects.create(
        event=event,
        subscription=subscription,
        target_type=subscription.target_type,
        status=RelayDelivery.Status.FAILED,
        external_id="REQ-556",
        external_url="https://jira.example.com/browse/REQ-556",
        error_message="boom",
        metadata={},
        idempotency_key="retry-attachments-2",
    )

    calls = {}

    def fake_update(self, issue_key, **kwargs):
        calls["update"] = kwargs
        return issue_key

    monkeypatch.setattr(
        "relay.services.drivers.jira_handler.JiraIssueHandler.update_issue",
        fake_update,
    )
    monkeypatch.setattr(
        "relay.services.drivers.jira_handler.JiraIssueHandler.upload_attachments",
        lambda self, issue_key, attachments: pytest.fail(
            "upload_attachments should not be called on Jira update"
        ),
    )
    monkeypatch.setattr(
        "relay.services.drivers.jira_handler.JiraIssueHandler.get_issue_url",
        lambda self, issue_key: f"https://jira.example.com/browse/{issue_key}",
    )

    delivery.metadata = {
        "uploaded_attachment_keys": ["jira_id:att-1", "name:demo.png:12"]
    }
    delivery.save(update_fields=["metadata"])

    summary = RelayDispatcher.retry_delivery(delivery, task_id="task-attachments-skip")

    refreshed = RelayDelivery.objects.get(id=delivery.id)
    assert summary["success"] == 1
    assert refreshed.metadata["uploaded_attachment_keys"] == [
        "jira_id:att-1",
        "name:demo.png:12",
    ]
    assert refreshed.metadata["upload_result"]["reason"] == "all_attachments_already_uploaded"
    assert refreshed.metadata["upload_result"]["skipped_count"] == 1


@pytest.mark.django_db
def test_relay_retry_recreates_jira_issue_when_target_is_missing(monkeypatch):
    user = User.objects.create_user(
        username="relay-user-jira-missing",
        email="relay-jira-missing@example.com",
        password="secret",
    )
    email = EmailMessageFactory(user=user)
    event = RelayEvent.objects.create(
        user=user,
        email_message=email,
        event_type=RelayEvent.EventType.WORKFLOW_COMPLETED,
        artifact_snapshot={
            "summary_title": "Missing issue title",
            "summary_content": "Missing issue content",
            "trigger_source": "retry",
        },
        status=RelayEvent.Status.FAILED,
    )
    subscription = RelaySubscription.objects.create(
        user=user,
        target_type=RelaySubscription.TargetType.JIRA,
        name="jira-missing",
        enabled=True,
        config={"jira": {"url": "https://jira.example.com"}},
        strategies={"retry_issue_strategy": "update"},
        field_mappings={},
    )
    delivery = RelayDelivery.objects.create(
        event=event,
        subscription=subscription,
        target_type=subscription.target_type,
        status=RelayDelivery.Status.FAILED,
        external_id="REQ-404",
        external_url="https://jira.example.com/browse/REQ-404",
        error_message="boom",
        metadata={"relay_retry_requested": True},
        idempotency_key="retry-missing-issue",
    )

    calls = {}

    def fake_update(self, issue_key, **kwargs):
        calls["update"] = kwargs
        raise RuntimeError("问题不存在")

    def fake_create(self, **kwargs):
        calls["create"] = kwargs
        return "REQ-405"

    monkeypatch.setattr(
        "relay.services.drivers.jira_handler.JiraIssueHandler.update_issue",
        fake_update,
    )
    monkeypatch.setattr(
        "relay.services.drivers.jira_handler.JiraIssueHandler.create_issue",
        fake_create,
    )
    monkeypatch.setattr(
        "relay.services.drivers.jira_handler.JiraIssueHandler.get_issue_url",
        lambda self, issue_key: f"https://jira.example.com/browse/{issue_key}",
    )

    summary = RelayDispatcher.retry_delivery(delivery, task_id="task-missing")

    refreshed = RelayDelivery.objects.get(id=delivery.id)
    assert summary["success"] == 1
    assert refreshed.external_id == "REQ-405"
    assert calls["create"]["issue_data"]["title"] == "Missing issue title"
    assert refreshed.metadata["relay_strategy"] == "update"
    assert refreshed.metadata["relay_strategy_source"] == "retry"


@pytest.mark.django_db
def test_relay_retry_recreates_feishu_record_when_target_is_missing(monkeypatch):
    user = User.objects.create_user(
        username="relay-user-feishu-missing",
        email="relay-feishu-missing@example.com",
        password="secret",
    )
    email = EmailMessageFactory(user=user)
    event = RelayEvent.objects.create(
        user=user,
        email_message=email,
        event_type=RelayEvent.EventType.WORKFLOW_COMPLETED,
        artifact_snapshot={
            "summary_title": "Missing Feishu title",
            "summary_content": "Missing Feishu content",
            "trigger_source": "retry",
        },
        status=RelayEvent.Status.FAILED,
    )
    subscription = RelaySubscription.objects.create(
        user=user,
        target_type=RelaySubscription.TargetType.FEISHU_BITABLE,
        name="feishu-missing",
        enabled=True,
        config={"feishu_bitable": {"app_token": "app-token"}},
        strategies={"retry_issue_strategy": "update"},
        field_mappings={},
    )
    delivery = RelayDelivery.objects.create(
        event=event,
        subscription=subscription,
        target_type=subscription.target_type,
        status=RelayDelivery.Status.FAILED,
        external_id="record-404",
        external_url="https://feishu.example.com/record/404",
        error_message="boom",
        metadata={"relay_retry_requested": True},
        idempotency_key="retry-feishu-missing",
    )

    calls = {}

    def fake_update(self, record_id, **kwargs):
        calls["update"] = kwargs
        raise RuntimeError("record not found")

    def fake_create(self, **kwargs):
        calls["create"] = kwargs
        return "record-405"

    monkeypatch.setattr(
        "relay.services.drivers.feishu_bitable_handler.FeishuBitableIssueHandler.update_issue",
        fake_update,
    )
    monkeypatch.setattr(
        "relay.services.drivers.feishu_bitable_handler.FeishuBitableIssueHandler.create_issue",
        fake_create,
    )
    monkeypatch.setattr(
        "relay.services.drivers.feishu_bitable_handler.FeishuBitableIssueHandler.get_issue_url",
        lambda self, record_id: f"https://feishu.example.com/record/{record_id}",
    )

    summary = RelayDispatcher.retry_delivery(delivery, task_id="task-feishu-missing")

    refreshed = RelayDelivery.objects.get(id=delivery.id)
    assert summary["success"] == 1
    assert refreshed.external_id == "record-405"
    assert calls["update"]["issue_data"]["title"] == "Missing Feishu title"
    assert calls["create"]["issue_data"]["title"] == "Missing Feishu title"
    assert refreshed.metadata["relay_strategy"] == "update"
    assert refreshed.metadata["relay_strategy_source"] == "retry"


@pytest.mark.django_db
def test_relay_dispatcher_creates_and_links_related_issues_for_jira(
    monkeypatch,
):
    user = User.objects.create_user(
        username="relay-user-merge-link",
        email="relay-merge-link@example.com",
        password="secret",
    )
    parent_email = EmailMessageFactory(user=user)
    child_email = EmailMessageFactory(user=user)
    child_email.merged_into = parent_email
    child_email.save(update_fields=["merged_into"])

    prior_event = RelayEvent.objects.create(
        user=user,
        email_message=parent_email,
        event_type=RelayEvent.EventType.WORKFLOW_COMPLETED,
        artifact_snapshot={
            "summary_title": "Parent title",
            "summary_content": "Parent content",
            "trigger_source": "workflow",
        },
        status=RelayEvent.Status.COMPLETED,
    )
    event = RelayEvent.objects.create(
        user=user,
        email_message=child_email,
        event_type=RelayEvent.EventType.WORKFLOW_COMPLETED,
        artifact_snapshot={
            "summary_title": "Child title",
            "summary_content": "Child content",
            "trigger_source": "workflow",
        },
    )
    subscription = RelaySubscription.objects.create(
        user=user,
        target_type=RelaySubscription.TargetType.JIRA,
        name="jira-linked",
        enabled=True,
        config={"jira": {"url": "https://jira.example.com"}},
        strategies={
            "auto_merge_strategy": "new",
            "manual_merge_strategy": "linked",
            "retry_issue_strategy": "update",
        },
        field_mappings={},
    )
    _create_successful_delivery(
        event=prior_event,
        subscription=subscription,
        external_id="REQ-111",
        external_url="https://jira.example.com/browse/REQ-111",
    )

    create_mock_calls = {}

    def fake_create(self, **kwargs):
        create_mock_calls["create"] = kwargs
        return "REQ-222"

    def fake_link(self, issue_key, related_issue_keys, *, link_type="Relates"):
        create_mock_calls["link"] = {
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
        lambda self, issue_key: f"https://jira.example.com/browse/{issue_key}",
    )

    summary = RelayDispatcher.dispatch_event(event, task_id="task-link")

    refreshed = RelayDelivery.objects.get(event=event, subscription=subscription)
    assert summary["success"] == 1
    assert refreshed.external_id == "REQ-222"
    assert refreshed.metadata["relay_strategy"] == "new_and_link"
    assert create_mock_calls["create"]["issue_data"]["title"] == "Child title"
    assert create_mock_calls["link"]["issue_key"] == "REQ-222"
    assert create_mock_calls["link"]["related_issue_keys"] == ["REQ-111"]


@pytest.mark.django_db
def test_relay_dispatcher_creates_and_partially_links_for_feishu(
    monkeypatch,
):
    user = User.objects.create_user(
        username="relay-user-feishu-link",
        email="relay-feishu-link@example.com",
        password="secret",
    )
    parent_email = EmailMessageFactory(user=user)
    child_email = EmailMessageFactory(user=user)
    child_email.merged_into = parent_email
    child_email.save(update_fields=["merged_into"])

    prior_event = RelayEvent.objects.create(
        user=user,
        email_message=parent_email,
        event_type=RelayEvent.EventType.WORKFLOW_COMPLETED,
        artifact_snapshot={
            "summary_title": "Parent title",
            "summary_content": "Parent content",
            "trigger_source": "workflow",
        },
        status=RelayEvent.Status.COMPLETED,
    )
    event = RelayEvent.objects.create(
        user=user,
        email_message=child_email,
        event_type=RelayEvent.EventType.WORKFLOW_COMPLETED,
        artifact_snapshot={
            "summary_title": "Child title",
            "summary_content": "Child content",
            "trigger_source": "workflow",
        },
    )
    subscription = RelaySubscription.objects.create(
        user=user,
        target_type=RelaySubscription.TargetType.FEISHU_BITABLE,
        name="feishu-linked",
        enabled=True,
        config={"feishu_bitable": {"app_token": "app-token"}},
        strategies={
            "auto_merge_strategy": "new",
            "manual_merge_strategy": "linked",
            "retry_issue_strategy": "update",
        },
        field_mappings={},
    )
    _create_successful_delivery(
        event=prior_event,
        subscription=subscription,
        external_id="record-111",
        external_url="https://feishu.example.com/record/111",
    )

    calls = {}

    def fake_create(self, **kwargs):
        calls["create"] = kwargs
        return "record-222"

    def fake_link(self, issue_key, related_issue_keys, *, link_type="Relates"):
        calls["link"] = {
            "issue_key": issue_key,
            "related_issue_keys": list(related_issue_keys),
            "link_type": link_type,
        }
        return {"linked_count": 0, "skipped_count": len(related_issue_keys)}

    monkeypatch.setattr(
        "relay.services.drivers.feishu_bitable_handler.FeishuBitableIssueHandler.create_issue",
        fake_create,
    )
    monkeypatch.setattr(
        "relay.services.drivers.feishu_bitable_handler.FeishuBitableIssueHandler.link_related_issues",
        fake_link,
    )
    monkeypatch.setattr(
        "relay.services.drivers.feishu_bitable_handler.FeishuBitableIssueHandler.get_issue_url",
        lambda self, record_id: f"https://feishu.example.com/record/{record_id}",
    )

    summary = RelayDispatcher.dispatch_event(event, task_id="task-feishu-link")

    refreshed = RelayDelivery.objects.get(event=event, subscription=subscription)
    assert summary["success"] == 1
    assert refreshed.external_id == "record-222"
    assert refreshed.metadata["relay_strategy"] == "new_and_link"
    assert refreshed.metadata["relay_linking_supported"] is False
    assert calls["create"]["issue_data"]["title"] == "Child title"
    assert calls["link"]["issue_key"] == "record-222"
    assert calls["link"]["related_issue_keys"] == ["record-111"]


@pytest.mark.django_db
def test_relay_dispatcher_applies_feishu_title_prefix(monkeypatch):
    user = User.objects.create_user(
        username="relay-user-feishu-prefix",
        email="relay-feishu-prefix@example.com",
        password="secret",
    )
    email = EmailMessageFactory(user=user)
    event = RelayEvent.objects.create(
        user=user,
        email_message=email,
        event_type=RelayEvent.EventType.WORKFLOW_COMPLETED,
        artifact_snapshot={
            "summary_title": "Child title",
            "summary_content": "Child content",
            "trigger_source": "workflow",
        },
    )
    subscription = RelaySubscription.objects.create(
        user=user,
        target_type=RelaySubscription.TargetType.FEISHU_BITABLE,
        name="feishu-prefix",
        enabled=True,
        config={
            "feishu_bitable": {
                "app_token": "app-token",
                "summary_prefix": "[DEVIFY TEST] ",
            }
        },
        strategies={
            "auto_merge_strategy": "new",
            "manual_merge_strategy": "linked",
            "retry_issue_strategy": "update",
        },
        field_mappings={},
    )

    calls = {}

    def fake_create(self, **kwargs):
        calls["create"] = kwargs
        return "record-333"

    monkeypatch.setattr(
        "relay.services.drivers.feishu_bitable_handler.FeishuBitableIssueHandler.create_issue",
        fake_create,
    )
    monkeypatch.setattr(
        "relay.services.drivers.feishu_bitable_handler.FeishuBitableIssueHandler.get_issue_url",
        lambda self, record_id: f"https://feishu.example.com/record/{record_id}",
    )

    summary = RelayDispatcher.dispatch_event(event, task_id="task-feishu-prefix")

    refreshed = RelayDelivery.objects.get(event=event, subscription=subscription)
    assert summary["success"] == 1
    assert refreshed.external_id == "record-333"
    assert calls["create"]["issue_data"]["title"] == "[DEVIFY TEST] Child title"
    assert calls["create"]["email_data"]["summary_title"] == "[DEVIFY TEST] Child title"


@pytest.mark.django_db
def test_relay_delivery_retry_api_triggers_task(monkeypatch, api_client):
    user = User.objects.create_user(
        username="relay-user-4",
        email="relay4@example.com",
        password="secret",
    )
    email = EmailMessageFactory(user=user)
    event = RelayEvent.objects.create(
        user=user,
        email_message=email,
        event_type=RelayEvent.EventType.WORKFLOW_COMPLETED,
        artifact_snapshot={"summary_title": "API retry", "summary_content": "API retry"},
    )
    subscription = RelaySubscription.objects.create(
        user=user,
        target_type=RelaySubscription.TargetType.JIRA,
        name="jira-api",
        enabled=True,
        config={"jira": {"url": "https://jira.example.com"}},
        strategies={"retry_issue_strategy": "update"},
        field_mappings={},
    )
    delivery = RelayDelivery.objects.create(
        event=event,
        subscription=subscription,
        target_type=subscription.target_type,
        status=RelayDelivery.Status.FAILED,
        error_message="boom",
        metadata={},
        idempotency_key="api-retry-1",
    )
    api_client.force_authenticate(user=user)

    queued = SimpleNamespace(id="task-999")
    monkeypatch.setattr(
        process_relay_delivery,
        "delay",
        lambda delivery_id: queued,
    )

    response = api_client.post(
        reverse("relay-delivery-retry", kwargs={"pk": delivery.id})
    )

    assert response.status_code == 202
    assert response.data["data"]["delivery_id"] == delivery.id
    assert response.data["data"]["task_id"] == "task-999"
    assert response.data["data"]["task_rebuilt"] is False


@pytest.mark.django_db
def test_relay_delivery_retry_api_marks_rebuilt_task_when_task_record_missing(
    monkeypatch,
    api_client,
):
    user = User.objects.create_user(
        username="relay-user-4b",
        email="relay4b@example.com",
        password="secret",
    )
    email = EmailMessageFactory(user=user)
    event = RelayEvent.objects.create(
        user=user,
        email_message=email,
        event_type=RelayEvent.EventType.WORKFLOW_COMPLETED,
        artifact_snapshot={"summary_title": "API retry", "summary_content": "API retry"},
    )
    subscription = RelaySubscription.objects.create(
        user=user,
        target_type=RelaySubscription.TargetType.JIRA,
        name="jira-api",
        enabled=True,
        config={"jira": {"url": "https://jira.example.com"}},
        strategies={"retry_issue_strategy": "update"},
        field_mappings={},
    )
    delivery = RelayDelivery.objects.create(
        event=event,
        subscription=subscription,
        target_type=subscription.target_type,
        status=RelayDelivery.Status.FAILED,
        error_message="boom",
        metadata={},
        agentcore_task_id="deleted-task-123",
        idempotency_key="api-retry-2",
    )
    api_client.force_authenticate(user=user)

    queued = SimpleNamespace(id="task-1000")
    monkeypatch.setattr(
        process_relay_delivery,
        "delay",
        lambda delivery_id: queued,
    )

    response = api_client.post(
        reverse("relay-delivery-retry", kwargs={"pk": delivery.id})
    )

    assert response.status_code == 202
    assert response.data["data"]["task_id"] == "task-1000"
    assert response.data["data"]["task_rebuilt"] is True
    assert not TaskExecution.objects.filter(task_id="deleted-task-123").exists()


@pytest.mark.django_db
def test_relay_event_list_includes_legacy_and_unpublished_events(api_client):
    user = User.objects.create_user(
        username="relay-user-5",
        email="relay5@example.com",
        password="secret",
    )
    email = EmailMessageFactory(user=user)
    legacy_event = RelayEvent.objects.create(
        user=user,
        email_message=email,
        event_type=RelayEvent.EventType.WORKFLOW_COMPLETED,
        artifact_snapshot={"title": "Legacy title"},
    )
    subscription = RelaySubscription.objects.create(
        user=user,
        target_type=RelaySubscription.TargetType.JIRA,
        name="Legacy Jira Channel",
        enabled=True,
        config={"jira": {"url": "https://jira.example.com"}},
        strategies={"retry_issue_strategy": "update"},
        field_mappings={},
    )
    RelayDelivery.objects.create(
        event=legacy_event,
        subscription=subscription,
        target_type=subscription.target_type,
        status=RelayDelivery.Status.SUCCESS,
        metadata={},
        idempotency_key="list-subject-1",
    )
    summary_event = RelayEvent.objects.create(
        user=user,
        email_message=email,
        event_type=RelayEvent.EventType.WORKFLOW_COMPLETED,
        artifact_snapshot={"summary_title": "Message title wins 2"},
    )
    RelayDelivery.objects.create(
        event=summary_event,
        subscription=subscription,
        target_type=subscription.target_type,
        status=RelayDelivery.Status.SUCCESS,
        metadata={},
        idempotency_key="list-subject-2",
    )
    api_client.force_authenticate(user=user)

    response = api_client.get(reverse("relay-events"))

    assert response.status_code == 200
    assert response.data["data"]["items"][0]["event_artifact_snapshot"][
        "summary_title"
    ] == "Message title wins 2"
    assert len(response.data["data"]["items"][0]["deliveries"]) == 1
    assert response.data["data"]["items"][1]["event_artifact_snapshot"]["title"] == "Legacy title"
    assert len(response.data["data"]["items"][1]["deliveries"]) == 1
    assert response.data["data"]["pagination"]["total"] == 2
    assert response.data["data"]["pagination"]["totalPages"] == 1


@pytest.mark.django_db
def test_relay_event_detail_returns_event_business_state(api_client):
    user = User.objects.create_user(
        username="relay-user-detail",
        email="relay-detail@example.com",
        password="secret",
    )
    email = EmailMessageFactory(user=user)
    event = RelayEvent.objects.create(
        user=user,
        email_message=email,
        event_type=RelayEvent.EventType.WORKFLOW_COMPLETED,
        artifact_snapshot={"summary_title": "Detail title"},
        status=RelayEvent.Status.PROCESSING,
    )
    subscription = RelaySubscription.objects.create(
        user=user,
        target_type=RelaySubscription.TargetType.JIRA,
        name="jira-detail",
        enabled=True,
        config={"jira": {"url": "https://jira.example.com"}},
        strategies={"retry_issue_strategy": "update"},
        field_mappings={},
    )
    RelayDelivery.objects.create(
        event=event,
        subscription=subscription,
        target_type=subscription.target_type,
        status=RelayDelivery.Status.PROCESSING,
        metadata={},
        idempotency_key="detail-event-1",
    )
    api_client.force_authenticate(user=user)

    response = api_client.get(reverse("relay-event-detail", kwargs={"pk": event.id}))

    assert response.status_code == 200
    assert response.data["data"]["status"] == RelayEvent.Status.PROCESSING
    assert response.data["data"]["deliveries"][0]["status"] == RelayDelivery.Status.PROCESSING


@pytest.mark.django_db
def test_relay_delivery_detail_returns_delivery_business_state(api_client):
    user = User.objects.create_user(
        username="relay-user-detail-2",
        email="relay-detail-2@example.com",
        password="secret",
    )
    email = EmailMessageFactory(user=user)
    event = RelayEvent.objects.create(
        user=user,
        email_message=email,
        event_type=RelayEvent.EventType.WORKFLOW_COMPLETED,
        artifact_snapshot={"summary_title": "Detail delivery"},
        status=RelayEvent.Status.PROCESSING,
    )
    subscription = RelaySubscription.objects.create(
        user=user,
        target_type=RelaySubscription.TargetType.JIRA,
        name="jira-detail-2",
        enabled=True,
        config={"jira": {"url": "https://jira.example.com"}},
        strategies={"retry_issue_strategy": "update"},
        field_mappings={},
    )
    delivery = RelayDelivery.objects.create(
        event=event,
        subscription=subscription,
        target_type=subscription.target_type,
        status=RelayDelivery.Status.PROCESSING,
        metadata={},
        idempotency_key="detail-delivery-1",
    )
    api_client.force_authenticate(user=user)

    response = api_client.get(
        reverse("relay-delivery-detail", kwargs={"pk": delivery.id})
    )

    assert response.status_code == 200
    assert response.data["data"]["status"] == RelayDelivery.Status.PROCESSING
    assert response.data["data"]["subscription"]["name"] == "jira-detail-2"
