from __future__ import annotations

from types import SimpleNamespace

import pytest

from relay.models import RelaySubscription
from relay.services.adapters import (
    FeishuBitableRelayAdapter,
    GitHubIssueRelayAdapter,
    JiraRelayAdapter,
)
from relay.services.localization import get_delivery_artifact, normalize_language


class _FakeDelivery(SimpleNamespace):
    def save(self, *, update_fields):
        self.saved_update_fields = update_fields


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("English", "English"),
        ("en-US", "English"),
        ("zh_CN", "Chinese"),
        ("Spanish", ""),
    ],
)
def test_normalize_language_supports_relay_language_aliases(value, expected):
    assert normalize_language(value) == expected


def test_delivery_artifact_localizes_per_channel_and_reuses_cached_result(
    monkeypatch,
):
    event = SimpleNamespace(
        email_message=SimpleNamespace(subject="登录页面无法打开"),
        artifact_snapshot={
            "summary_title": "登录页面无法打开",
            "summary_content": "用户报告登录页面返回空白。",
            "llm_content": "用户报告登录页面返回空白。",
            "language": "Chinese",
        },
    )
    english_subscription = SimpleNamespace(
        target_type=RelaySubscription.TargetType.JIRA,
        config={"language": "en", "jira": {}},
    )
    chinese_subscription = SimpleNamespace(
        target_type=RelaySubscription.TargetType.FEISHU_BITABLE,
        config={"language": "Chinese", "feishu_bitable": {}},
    )
    english_delivery = _FakeDelivery(id=1, metadata={})
    chinese_delivery = _FakeDelivery(id=2, metadata={})
    llm_calls = []

    def fake_call_and_track(**kwargs):
        llm_calls.append(kwargs)
        return (
            {
                "summary_title": "Login page does not open",
                "summary_content": "The user reports a blank login page.",
                "llm_content": "The user reports a blank login page.",
            },
            {"total_tokens": 10},
        )

    monkeypatch.setattr(
        "relay.services.localization.LLMTracker.call_and_track",
        fake_call_and_track,
    )
    monkeypatch.setattr(
        "relay.services.localization._configured_model_uuid",
        lambda: None,
    )

    english_artifact = get_delivery_artifact(
        event=event,
        subscription=english_subscription,
        delivery=english_delivery,
    )
    chinese_artifact = get_delivery_artifact(
        event=event,
        subscription=chinese_subscription,
        delivery=chinese_delivery,
    )
    cached_english_artifact = get_delivery_artifact(
        event=event,
        subscription=english_subscription,
        delivery=english_delivery,
    )

    assert english_artifact["summary_title"] == "Login page does not open"
    assert english_artifact["summary_content"] == (
        "The user reports a blank login page."
    )
    assert english_artifact["language"] == "English"
    assert chinese_artifact["summary_title"] == "登录页面无法打开"
    assert cached_english_artifact == english_artifact
    assert len(llm_calls) == 1
    assert event.artifact_snapshot["summary_title"] == "登录页面无法打开"

    assert english_delivery.metadata["relay_localization"]["status"] == "localized"
    assert english_delivery.metadata["relay_localization"]["artifact"] == (
        english_artifact
    )
    assert english_delivery.saved_update_fields == ["metadata", "updated_at"]


def test_delivery_artifact_caches_original_artifact_when_localization_fails(
    monkeypatch,
):
    event = SimpleNamespace(
        email_message=SimpleNamespace(subject="支付失败"),
        artifact_snapshot={
            "summary_title": "支付失败",
            "summary_content": "用户无法完成支付。",
            "language": "Chinese",
        },
    )
    subscription = SimpleNamespace(
        target_type=RelaySubscription.TargetType.GITHUB_ISSUE,
        config={"language": "English", "github": {}},
    )
    delivery = _FakeDelivery(id=3, metadata={})
    llm_calls = []

    def fail_localization(**kwargs):
        llm_calls.append(kwargs)
        raise RuntimeError("LLM unavailable")

    monkeypatch.setattr(
        "relay.services.localization.LLMTracker.call_and_track",
        fail_localization,
    )
    monkeypatch.setattr(
        "relay.services.localization._configured_model_uuid",
        lambda: None,
    )

    first_artifact = get_delivery_artifact(
        event=event,
        subscription=subscription,
        delivery=delivery,
    )
    second_artifact = get_delivery_artifact(
        event=event,
        subscription=subscription,
        delivery=delivery,
    )

    assert first_artifact["summary_title"] == "支付失败"
    assert second_artifact == first_artifact
    assert len(llm_calls) == 1
    assert delivery.metadata["relay_localization"]["status"] == "fallback"


@pytest.mark.parametrize(
    ("adapter_class", "handler_path", "target_type"),
    [
        (
            FeishuBitableRelayAdapter,
            "relay.services.drivers.feishu_bitable_handler.FeishuBitableIssueHandler",
            RelaySubscription.TargetType.FEISHU_BITABLE,
        ),
        (
            JiraRelayAdapter,
            "relay.services.adapters.JiraIssueHandler",
            RelaySubscription.TargetType.JIRA,
        ),
        (
            GitHubIssueRelayAdapter,
            "relay.services.adapters.GitHubIssueHandler",
            RelaySubscription.TargetType.GITHUB_ISSUE,
        ),
    ],
)
def test_relay_adapters_use_delivery_localized_title_content_and_language(
    monkeypatch,
    adapter_class,
    handler_path,
    target_type,
):
    captured = {}

    class FakeHandler:
        repo = "cloud2ai/devify"

        def __init__(self, config):
            self.config = config

        def create_issue(self, **kwargs):
            captured.update(kwargs)
            return "external-1"

        def get_issue_url(self, external_id):
            return f"https://example.com/{external_id}"

    monkeypatch.setattr(handler_path, FakeHandler)
    monkeypatch.setattr(
        "relay.services.localization.LLMTracker.call_and_track",
        lambda **kwargs: (
            {
                "summary_title": "Localized title",
                "summary_content": "Localized content",
                "llm_content": "Localized content",
            },
            {"total_tokens": 10},
        ),
    )
    monkeypatch.setattr(
        "relay.services.localization._configured_model_uuid",
        lambda: None,
    )

    event = SimpleNamespace(
        id=1,
        email_message_id=1,
        email_message=SimpleNamespace(subject="原始标题"),
        artifact_snapshot={
            "summary_title": "原始标题",
            "summary_content": "原始内容",
            "llm_content": "原始内容",
            "language": "Chinese",
        },
    )
    subscription = SimpleNamespace(
        target_type=target_type,
        config={"language": "English"},
        strategies={},
    )
    delivery = SimpleNamespace(
        external_id=None,
        metadata={
            "relay_delivery_plan": {
                "action": "new",
                "source": "test",
                "reference_external_id": "",
                "related_issue_keys": [],
                "related_issue_references": [],
                "linking_supported": False,
            }
        },
    )

    adapter_class().deliver(
        event=event,
        subscription=subscription,
        delivery=delivery,
    )

    assert captured["issue_data"]["title"] == "Localized title"
    assert captured["issue_data"]["description"] == "Localized content"
    assert captured["email_data"]["language"] == "English"
