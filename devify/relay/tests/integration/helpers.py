"""Helpers for Relay integration tests."""

from __future__ import annotations

from copy import deepcopy
import os
from typing import Iterable

import pytest
from django.contrib.auth import get_user_model

from relay.models import RelaySubscription
from relay.services.test_attachments import BUILTIN_TEST_ATTACHMENT

User = get_user_model()

TEST_PREFIX = "DEVIFY TEST"


def make_test_label(*parts: str) -> str:
    suffix = " ".join(str(part).strip() for part in parts if str(part).strip())
    return f"{TEST_PREFIX} {suffix}".strip() if suffix else TEST_PREFIX


def make_test_email_address(*parts: str) -> str:
    slug = "-".join(
        str(part).strip().lower().replace(" ", "-")
        for part in parts
        if str(part).strip()
    )
    return f"{slug or 'devify-test'}@example.com"


def require_env(keys: Iterable[str], *, scenario: str) -> None:
    missing = [key for key in keys if not os.getenv(key)]
    if missing:
        pytest.skip(
            f"Skipping {scenario} integration test; missing env vars: "
            + ", ".join(missing)
        )


def build_sample_jira_subscription_config() -> dict:
    return {
        "jira": {
            "url": "https://jira.devify.test",
            "username": "devify-test-jira",
            "api_token": "devify-test-token",
        },
        "language": "Chinese",
        "fields": {
            "project_key_config": {
                "use_llm": False,
                "jira_field": "project",
                "default": "REQ",
            },
            "issue_type_config": {
                "use_llm": False,
                "jira_field": "issuetype",
                "default": "Task",
            },
            "priority_config": {
                "use_llm": False,
                "jira_field": "priority",
                "default": "Medium",
            },
            "summary_config": {
                "prefix": os.getenv("JIRA_SUMMARY_PREFIX", "[DEVIFY TEST]"),
                "use_llm": True,
                "jira_field": "summary",
            },
            "description_config": {
                "use_llm": False,
                "jira_field": "description",
                "convert_to_jira_wiki": True,
            },
        },
    }


def build_sample_feishu_subscription_config(*, token_type: str = "bitable") -> dict:
    return {
        "issue_engine": "feishu_bitable",
        "feishu_bitable": {
            "app_id": "cli_devify_test_app_id",
            "app_secret": "cli_devify_test_app_secret",
            "app_token_type": token_type,
            "app_token": "cli_devify_test_app_token",
            "table_name": "DEVIFY TEST Relay Table",
            "summary_prefix": os.getenv("FEISHU_SUMMARY_PREFIX", "[DEVIFY TEST] "),
            "attachment_field_name": "附件",
            "field_mappings": {
                "标题": "title",
                "描述": "description",
            },
        },
    }


def build_real_jira_subscription_config() -> dict:
    summary_prefix = os.getenv("JIRA_SUMMARY_PREFIX", "[DEVIFY TEST]")
    db_config = _load_db_subscription_config(
        target_type=RelaySubscription.TargetType.JIRA,
        preferred_username="admin",
    )
    if db_config:
        config = deepcopy(db_config)
        config.setdefault("fields", {}).setdefault("summary_config", {})[
            "prefix"
        ] = summary_prefix
        return config

    require_env(
        ("JIRA_URL", "JIRA_USERNAME", "JIRA_PASSWORD"),
        scenario="relay jira",
    )
    return {
        "jira": {
            "url": os.environ["JIRA_URL"],
            "username": os.environ["JIRA_USERNAME"],
            "api_token": os.environ["JIRA_PASSWORD"],
        },
        "language": "Chinese",
        "fields": {
            "project_key_config": {
                "use_llm": False,
                "jira_field": "project",
                "default": os.getenv("JIRA_PROJECT_KEY", "REQ"),
            },
            "issue_type_config": {
                "use_llm": False,
                "jira_field": "issuetype",
                "default": os.getenv("JIRA_ISSUE_TYPE", "Task"),
            },
            "priority_config": {
                "use_llm": False,
                "jira_field": "priority",
                "default": os.getenv("JIRA_PRIORITY", "Medium"),
            },
            "summary_config": {
                "prefix": summary_prefix,
                "use_llm": True,
                "jira_field": "summary",
            },
            "description_config": {
                "use_llm": False,
                "jira_field": "description",
                "convert_to_jira_wiki": True,
            },
        },
    }


def build_real_feishu_subscription_config(*, token_type: str) -> dict:
    test_prefix = os.getenv("FEISHU_SUMMARY_PREFIX", "[DEVIFY TEST] ")
    db_config = _load_db_feishu_subscription_config(token_type=token_type)
    if db_config:
        config = deepcopy(db_config)
        feishu_config = config.setdefault("feishu_bitable", {})
        if not str(feishu_config.get("summary_prefix") or "").strip():
            feishu_config["summary_prefix"] = test_prefix
        return config

    app_token_env = (
        "FEISHU_BITABLE_APP_TOKEN"
        if token_type == "bitable"
        else "FEISHU_WIKI_APP_TOKEN"
    )
    required_env = (
        "FEISHU_APP_ID",
        "FEISHU_APP_SECRET",
        app_token_env,
        "FEISHU_TABLE_NAME",
    )
    require_env(required_env, scenario=f"relay feishu {token_type}")
    return {
        "issue_engine": "feishu_bitable",
        "feishu_bitable": {
            "app_id": os.environ["FEISHU_APP_ID"],
            "app_secret": os.environ["FEISHU_APP_SECRET"],
            "app_token_type": token_type,
            "app_token": os.environ[app_token_env],
            "table_name": os.environ["FEISHU_TABLE_NAME"],
            "summary_prefix": test_prefix,
            "attachment_field_name": os.getenv(
                "FEISHU_ATTACHMENT_FIELD_NAME", "附件"
            ),
            "field_mappings": {
                "标题": "title",
                "描述": "description",
            },
        },
    }


def _load_db_subscription_config(
    *,
    target_type: str,
    preferred_username: str | None = None,
) -> dict | None:
    queryset = RelaySubscription.objects.filter(
        target_type=target_type,
        enabled=True,
    )
    if preferred_username:
        queryset = queryset.filter(user__username=preferred_username)

    subscription = queryset.order_by("-updated_at", "-id").first()
    if subscription:
        return deepcopy(subscription.config or {})
    return None


def _load_db_feishu_subscription_config(*, token_type: str) -> dict | None:
    queryset = RelaySubscription.objects.filter(
        target_type=RelaySubscription.TargetType.FEISHU_BITABLE,
        enabled=True,
    )
    subscription = None
    for candidate in queryset.order_by("-updated_at", "-id"):
        config = candidate.config or {}
        feishu_config = config.get("feishu_bitable", {})
        if str(feishu_config.get("app_token_type") or "").strip().lower() == token_type:
            subscription = candidate
            break

    if subscription:
        return deepcopy(subscription.config or {})
    return None


def build_test_snapshot() -> dict:
    return {
        "summary_title": os.getenv(
            "RELAY_TEST_SUMMARY_TITLE", "DEVIFY TEST summary"
        ),
        "summary_content": os.getenv(
            "RELAY_TEST_SUMMARY_CONTENT", "DEVIFY TEST description"
        ),
        "llm_content": os.getenv(
            "RELAY_TEST_LLM_CONTENT", "DEVIFY TEST description"
        ),
        "attachments": [BUILTIN_TEST_ATTACHMENT],
    }
