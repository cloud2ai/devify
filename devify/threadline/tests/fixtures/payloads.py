"""
Reusable request payload builders for threadline tests.

These helpers keep API test data consistent across integration and unit tests
while still allowing per-test overrides.
"""

from copy import deepcopy

from django.utils import timezone


def _deep_merge(base: dict, overrides: dict) -> dict:
    merged = deepcopy(base)
    for key, value in overrides.items():
        if (
            isinstance(value, dict)
            and isinstance(merged.get(key), dict)
        ):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def build_issue_config(**overrides) -> dict:
    """Build the issue_config settings payload used by merge strategy tests."""

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
    return _deep_merge(config, overrides)


def build_settings_payload(
    *,
    key: str = "email_processing_config",
    value: dict | None = None,
    description: str = "Email processing configuration",
    is_active: bool = True,
    **overrides,
) -> dict:
    """Build a settings API payload."""

    payload = {
        "key": key,
        "value": value
        if value is not None
        else {
            "auto_process": True,
            "notification_enabled": True,
            "default_priority": "medium",
        },
        "description": description,
        "is_active": is_active,
    }
    return _deep_merge(payload, overrides)


def build_threadline_payload(
    *,
    user_id=None,
    task_id=None,
    message_id: str = "workflow-test-message-123",
    subject: str = "Workflow Test Email",
    sender: str = "sender@example.com",
    recipients: str = "recipient@example.com",
    received_at: str | None = None,
    raw_content: str = "Raw email content for workflow test",
    html_content: str = "<p>HTML content for workflow test</p>",
    text_content: str = "Plain text content for workflow test",
    **overrides,
) -> dict:
    """Build a threadline creation payload."""

    payload = {
        "message_id": message_id,
        "subject": subject,
        "sender": sender,
        "recipients": recipients,
        "received_at": received_at or timezone.now().isoformat(),
        "raw_content": raw_content,
        "html_content": html_content,
        "text_content": text_content,
    }
    if user_id is not None:
        payload["user_id"] = user_id
    if task_id is not None:
        payload["task_id"] = task_id
    return _deep_merge(payload, overrides)


def build_share_link_payload(expiration: str = "7d", **overrides) -> dict:
    """Build the payload for creating a threadline share link."""

    payload = {"expiration": expiration}
    return _deep_merge(payload, overrides)


def build_periodic_tasks_payload(
    *,
    enabled: bool = False,
    crontab: str = "*/5 * * * *",
    name: str = "threadline-schedule-email-fetch",
) -> dict:
    """Build the payload used by periodic task admin tests."""

    return {
        "tasks": [
            {
                "name": name,
                "enabled": enabled,
                "crontab": crontab,
            }
        ]
    }
