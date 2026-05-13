from __future__ import annotations

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from relay.models import RelayDelivery, RelayEvent, RelaySubscription
from relay.services.legacy_issue_sync import (
    sync_all_legacy_issues,
    sync_legacy_issues_for_user,
)
from threadline.models import EmailMessage, Issue, Settings


User = get_user_model()


def _create_email_message(user):
    return EmailMessage.objects.create(
        user=user,
        message_id=f"msg-{user.id}-{timezone.now().timestamp()}",
        subject="Legacy issue email",
        sender="sender@example.com",
        recipients="recipient@example.com",
        received_at=timezone.now(),
        html_content="",
        text_content="",
    )


def _build_issue_config():
    return {
        "enable": True,
        "issue_engine": "jira",
        "language": "Chinese",
        "auto_merge_strategy": "update",
        "manual_merge_strategy": "unlinked",
        "retry_issue_strategy": "new",
        "jira": {
            "url": "https://jira.example.com",
            "username": "test_user",
            "api_token": "test_token",
        },
        "fields": {
            "project_key_config": {"jira_field": "project", "default": "REQ"},
            "issue_type_config": {
                "jira_field": "issuetype",
                "default": "Task",
            },
            "priority_config": {
                "jira_field": "priority",
                "default": "Medium",
            },
        },
    }


@pytest.mark.django_db
def test_sync_legacy_issues_for_user_creates_relay_history():
    user = User.objects.create_user(
        username="relay-issue-user",
        email="relay-issue@example.com",
        password="secret",
    )
    email = _create_email_message(user)
    Issue.objects.create(
        user=user,
        email_message=email,
        title="Legacy Jira issue",
        description="Legacy issue description",
        priority="high",
        engine="jira",
        external_id="REQ-123",
        issue_url="https://jira.example.com/browse/REQ-123",
        metadata={"source": "legacy"},
    )

    result = sync_legacy_issues_for_user(user)

    assert result["status"] == "success"
    assert result["created"] == 1
    assert RelaySubscription.objects.filter(user=user, target_type="jira").count() == 1
    assert RelayEvent.objects.count() == 1
    assert RelayDelivery.objects.count() == 1

    delivery = RelayDelivery.objects.select_related("event", "subscription").get()
    assert delivery.status == RelayDelivery.Status.SUCCESS
    assert delivery.idempotency_key == "legacy_issue:1"
    assert delivery.external_id == "REQ-123"
    assert delivery.external_url == "https://jira.example.com/browse/REQ-123"
    assert delivery.subscription.name == "Legacy Jira Channel"
    assert delivery.event.artifact_snapshot["legacy_issue_id"] == 1
    assert delivery.event.artifact_snapshot["title"] == "Legacy Jira issue"


@pytest.mark.django_db
def test_sync_legacy_issues_for_user_prefers_legacy_issue_config_strategies():
    user = User.objects.create_user(
        username="relay-issue-user-strategy",
        email="relay-issue-strategy@example.com",
        password="secret",
    )
    email = _create_email_message(user)
    Settings.objects.create(
        user=user,
        key="issue_config",
        value=_build_issue_config(),
        description="legacy issue config",
        is_active=True,
    )
    Issue.objects.create(
        user=user,
        email_message=email,
        title="Legacy Jira issue",
        description="Legacy issue description",
        priority="high",
        engine="jira",
    )

    result = sync_legacy_issues_for_user(user)

    assert result["status"] == "success"
    subscription = RelaySubscription.objects.get(user=user)
    assert subscription.strategies == {
        "auto_merge_strategy": "update",
        "manual_merge_strategy": "unlinked",
        "retry_issue_strategy": "new",
    }


@pytest.mark.django_db
def test_sync_legacy_issues_for_user_is_idempotent():
    user = User.objects.create_user(
        username="relay-issue-user-2",
        email="relay-issue2@example.com",
        password="secret",
    )
    email = _create_email_message(user)
    Issue.objects.create(
        user=user,
        email_message=email,
        title="Legacy Jira issue",
        description="Legacy issue description",
        priority="medium",
        engine="jira",
    )

    first = sync_legacy_issues_for_user(user)
    second = sync_legacy_issues_for_user(user)

    assert first["status"] == "success"
    assert first["created"] == 1
    assert second["status"] == "skipped"
    assert RelayEvent.objects.count() == 1
    assert RelayDelivery.objects.count() == 1


@pytest.mark.django_db
@patch("relay.services.legacy_issue_sync.acquire_task_lock", return_value=True)
@patch("relay.services.legacy_issue_sync.release_task_lock")
def test_sync_all_legacy_issues_uses_background_lock(mock_release, mock_acquire):
    user = User.objects.create_user(
        username="relay-issue-user-3",
        email="relay-issue3@example.com",
        password="secret",
    )
    email = _create_email_message(user)
    Issue.objects.create(
        user=user,
        email_message=email,
        title="Legacy Feishu issue",
        description="Legacy issue description",
        priority="low",
        engine="feishu_bitable",
    )

    result = sync_all_legacy_issues()

    assert result["status"] == "success"
    assert result["created"] == 1
    mock_acquire.assert_called_once()
    mock_release.assert_called_once()
    assert RelayDelivery.objects.count() == 1
