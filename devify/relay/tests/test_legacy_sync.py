from __future__ import annotations

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model

from relay.models import RelaySubscription
from relay.services.legacy_sync import (
    sync_all_legacy_issue_configs,
    sync_legacy_issue_config_for_user,
    sync_legacy_channels_for_user,
)
from threadline.models import Settings


User = get_user_model()


def _build_issue_config(**overrides):
    config = {
        "enable": True,
        "issue_engine": "jira",
        "language": "Chinese",
        "auto_merge_strategy": "update",
        "manual_merge_strategy": "linked",
        "retry_issue_strategy": "update",
        "jira": {
            "url": "https://jira.example.com",
            "username": "test_user",
            "api_token": "test_token",
        },
        "fields": {
            "project_key_config": {
                "jira_field": "project",
                "default": "REQ",
            },
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
    for key, value in overrides.items():
        config[key] = value
    return config


@pytest.mark.django_db
def test_sync_legacy_issue_config_for_user_creates_relay_subscription():
    user = User.objects.create_user(
        username="relay-legacy-user",
        email="relay-legacy@example.com",
        password="secret",
    )
    legacy_config = _build_issue_config()
    Settings.objects.create(
        user=user,
        key="issue_config",
        value=legacy_config,
        description="legacy issue config",
        is_active=True,
    )

    result = sync_legacy_issue_config_for_user(user)

    assert result["status"] == "success"
    assert result["created"] == 1
    subscription = RelaySubscription.objects.get(user=user)
    assert subscription.target_type == RelaySubscription.TargetType.JIRA
    assert subscription.name == "Legacy Jira Channel"
    assert subscription.enabled is True
    assert subscription.config == legacy_config
    assert subscription.strategies == {
        "auto_merge_strategy": "update",
        "manual_merge_strategy": "linked",
        "retry_issue_strategy": "update",
    }
    assert subscription.field_mappings == {}


@pytest.mark.django_db
def test_sync_legacy_issue_config_is_idempotent():
    user = User.objects.create_user(
        username="relay-legacy-user-2",
        email="relay-legacy2@example.com",
        password="secret",
    )
    legacy_config = _build_issue_config()
    Settings.objects.create(
        user=user,
        key="issue_config",
        value=legacy_config,
        description="legacy issue config",
        is_active=True,
    )

    first = sync_legacy_issue_config_for_user(user)
    second = sync_legacy_issue_config_for_user(user)

    assert first["status"] == "success"
    assert first["created"] == 1
    assert second["status"] == "success"
    assert second["updated"] == 1
    assert RelaySubscription.objects.filter(user=user).count() == 1


@pytest.mark.django_db
@patch("relay.services.legacy_sync.acquire_task_lock", return_value=True)
@patch("relay.services.legacy_sync.release_task_lock")
def test_sync_all_legacy_issue_configs_uses_background_lock(
    mock_release, mock_acquire
):
    user = User.objects.create_user(
        username="relay-legacy-user-3",
        email="relay-legacy3@example.com",
        password="secret",
    )
    Settings.objects.create(
        user=user,
        key="issue_config",
        value=_build_issue_config(),
        description="legacy issue config",
        is_active=True,
    )

    result = sync_all_legacy_issue_configs()

    assert result["status"] == "success"
    assert result["created"] == 1
    assert result["updated"] == 0
    mock_acquire.assert_called_once()
    mock_release.assert_called_once()
    assert RelaySubscription.objects.filter(user=user).count() == 1


@pytest.mark.django_db
def test_sync_legacy_channels_for_user_prefers_jira_config_when_issue_config_missing():
    user = User.objects.create_user(
        username="relay-legacy-user-4",
        email="relay-legacy4@example.com",
        password="secret",
    )
    jira_config = {
        "url": "https://jira.example.com",
        "username": "jira-user",
        "api_token": "jira-token",
        "project_key": "REQ",
    }
    Settings.objects.create(
        user=user,
        key="jira_config",
        value=jira_config,
        description="legacy jira config",
        is_active=True,
    )

    result = sync_legacy_channels_for_user(user)

    assert result["status"] == "success"
    assert result["created"] == 1
    subscription = RelaySubscription.objects.get(user=user)
    assert subscription.target_type == RelaySubscription.TargetType.JIRA
    assert subscription.name == "Legacy Jira Channel"
    assert subscription.config == {
        "issue_engine": "jira",
        "enable": True,
        "jira": jira_config,
    }
