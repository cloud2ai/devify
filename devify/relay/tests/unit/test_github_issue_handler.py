"""Relay-owned tests for the GitHub Issue delivery target."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from django.test import override_settings
from relay.models import RelaySubscription
from relay.serializers import RelaySubscriptionSerializer
from relay.services.adapters import GitHubIssueRelayAdapter, RelayAdapterRegistry
from relay.services.drivers.github_issue_handler import GitHubIssueHandler
from threadline.utils.issues import get_issue_handler
from threadline.utils.issues.github_issue_handler import (
    GITHUB_ISSUE_BODY_MAX_LENGTH,
)


@pytest.fixture
def github_config():
    return {
        "issue_engine": "github_issue",
        "github": {
            "repo": "cloud2ai/devify",
            "token": "test-token",
            "labels": ["relay", "needs-review"],
            "assignees": ["octocat"],
        },
    }


def _response(*, status_code=200, payload=None):
    response = Mock()
    response.status_code = status_code
    response.json.return_value = payload or {}
    response.text = ""
    return response


@override_settings(
    EMAIL_ATTACHMENT_DIR="/srv/devify/attachments",
    ATTACHMENT_BASE_URL="https://files.devify.example",
)
def test_create_issue_posts_structured_markdown_and_public_attachment_urls(
    github_config,
):
    session = Mock()
    session.request.return_value = _response(
        status_code=201,
        payload={
            "number": 42,
            "html_url": "https://github.com/cloud2ai/devify/issues/42",
        },
    )
    handler = GitHubIssueHandler(github_config, session=session)

    issue_number = handler.create_issue(
        issue_data={"title": "Relay request", "description": "Fallback"},
        email_data={
            "summary_content": "Fallback summary",
            "summary_data": {
                "details": "Ship GitHub delivery.",
                "key_process": ["Create an issue", "Verify the result"],
            },
            "todos": [{"content": "Add tests", "owner": "Ray"}],
            "language": "en",
        },
        attachments=[
            {
                "filename": "diagram.png",
                "safe_filename": "diagram.png",
                "file_path": "/srv/devify/attachments/mail/diagram.png",
                "is_image": True,
            }
        ],
    )

    assert issue_number == "42"
    request = session.request.call_args
    assert request.args == (
        "POST",
        "https://api.github.com/repos/cloud2ai/devify/issues",
    )
    assert request.kwargs["timeout"] == 15
    assert request.kwargs["headers"]["Authorization"] == "Bearer test-token"
    assert request.kwargs["json"]["title"] == "Relay request"
    assert request.kwargs["json"]["labels"] == ["relay", "needs-review"]
    assert request.kwargs["json"]["assignees"] == ["octocat"]
    body = request.kwargs["json"]["body"]
    assert "## Core Topic" in body
    assert "Ship GitHub delivery." in body
    assert "## TODO" in body
    assert "Add tests" in body
    assert "## Key Process & Information" in body
    assert (
        "![diagram.png](https://files.devify.example/attachments/mail/diagram.png)"
        in body
    )


def test_update_issue_patches_the_existing_issue(github_config):
    session = Mock()
    session.request.return_value = _response(
        payload={
            "number": 42,
            "html_url": "https://github.com/cloud2ai/devify/issues/42",
        }
    )
    handler = GitHubIssueHandler(github_config, session=session)

    issue_number = handler.update_issue(
        "42",
        issue_data={"title": "Updated title", "description": "Updated body"},
        email_data={"summary_content": "Updated body"},
        attachments=[],
    )

    assert issue_number == "42"
    request = session.request.call_args
    assert request.args == (
        "PATCH",
        "https://api.github.com/repos/cloud2ai/devify/issues/42",
    )
    assert request.kwargs["json"]["title"] == "Updated title"
    assert request.kwargs["json"]["body"] == "Updated body"


def test_create_issue_embeds_related_issue_references(github_config):
    session = Mock()
    session.request.return_value = _response(
        status_code=201,
        payload={"number": 43},
    )
    handler = GitHubIssueHandler(github_config, session=session)

    handler.create_issue(
        issue_data={"title": "Follow-up", "description": "New work"},
        email_data={"related_issue_keys": ["7", "12"]},
        attachments=[],
    )

    body = session.request.call_args.kwargs["json"]["body"]
    assert "## Related issues" in body
    assert "- #7" in body
    assert "- #12" in body


def test_create_issue_truncates_body_to_github_limit(github_config):
    session = Mock()
    session.request.return_value = _response(
        status_code=201,
        payload={"number": 44},
    )
    handler = GitHubIssueHandler(github_config, session=session)

    handler.create_issue(
        issue_data={
            "title": "Large request",
            "description": "x" * (GITHUB_ISSUE_BODY_MAX_LENGTH + 100),
        },
        email_data={
            "related_issue_references": [
                {
                    "external_id": 7,
                    "github_repo": "cloud2ai/old-repo",
                }
            ]
        },
        attachments=[
            {
                "filename": "report.pdf",
                "url": "https://files.devify.example/report.pdf",
            }
        ],
    )

    body = session.request.call_args.kwargs["json"]["body"]
    assert len(body) == GITHUB_ISSUE_BODY_MAX_LENGTH
    assert "exceeded GitHub's issue body limit" in body
    assert "[report.pdf](https://files.devify.example/report.pdf)" in body
    assert "## Related issues\n\n- cloud2ai/old-repo#7" in body


@override_settings(
    EMAIL_ATTACHMENT_DIR="/srv/devify/attachments",
    ATTACHMENT_BASE_URL="https://files.devify.example",
)
def test_create_issue_omits_attachment_paths_outside_public_storage(
    github_config,
):
    session = Mock()
    session.request.return_value = _response(
        status_code=201,
        payload={"number": 45},
    )
    handler = GitHubIssueHandler(github_config, session=session)

    handler.create_issue(
        issue_data={"title": "Test request", "description": "Body"},
        email_data={},
        attachments=[
            {
                "filename": "temporary.txt",
                "file_path": "/tmp/temporary.txt",
            },
            {
                "filename": "private.txt",
                "file_path": ("/srv/devify/attachments/../private/private.txt"),
            },
        ],
    )

    body = session.request.call_args.kwargs["json"]["body"]
    assert body == "Body"
    assert "https://files.devify.example" not in body


def test_handler_rejects_invalid_repo_and_missing_token():
    with pytest.raises(ValueError, match="owner/name"):
        GitHubIssueHandler(
            {"github": {"repo": "https://github.com/cloud2ai/devify", "token": "x"}}
        )

    with pytest.raises(ValueError, match="token"):
        GitHubIssueHandler({"github": {"repo": "cloud2ai/devify", "token": ""}})


def test_factory_and_registry_resolve_github_target(github_config):
    assert isinstance(get_issue_handler(github_config), GitHubIssueHandler)
    assert isinstance(
        RelayAdapterRegistry.get_adapter("github_issue"),
        GitHubIssueRelayAdapter,
    )


def test_adapter_updates_existing_github_issue(monkeypatch, github_config):
    update_issue = Mock(return_value="42")
    create_issue = Mock(return_value="99")
    monkeypatch.setattr(GitHubIssueHandler, "update_issue", update_issue)
    monkeypatch.setattr(GitHubIssueHandler, "create_issue", create_issue)
    monkeypatch.setattr(
        GitHubIssueHandler,
        "get_issue_url",
        lambda self, issue_number: (
            f"https://github.com/cloud2ai/devify/issues/{issue_number}"
        ),
    )
    event = SimpleNamespace(
        email_message=SimpleNamespace(subject="Original subject"),
        email_message_id=7,
        artifact_snapshot={
            "summary_title": "Updated title",
            "summary_content": "Updated body",
            "attachments": [],
        },
    )
    subscription = SimpleNamespace(
        target_type="github_issue",
        config=github_config,
        strategies={},
    )
    delivery = SimpleNamespace(
        external_id="42",
        metadata={
            "relay_delivery_plan": {
                "action": "update",
                "source": "retry",
                "reference_external_id": "42",
                "reference_delivery_id": 1,
                "related_issue_keys": ["7"],
                "related_issue_references": [
                    {
                        "external_id": "42",
                        "provider": "github_issue",
                        "github_repo": "cloud2ai/devify",
                    },
                    {
                        "external_id": "7",
                        "provider": "github_issue",
                        "github_repo": "cloud2ai/devify",
                    },
                ],
                "linking_supported": True,
            }
        },
    )

    result = GitHubIssueRelayAdapter().deliver(
        event=event,
        subscription=subscription,
        delivery=delivery,
    )

    update_issue.assert_called_once()
    create_issue.assert_not_called()
    update_email_data = update_issue.call_args.kwargs["email_data"]
    assert update_email_data["related_issue_references"] == [
        {
            "external_id": "7",
            "provider": "github_issue",
            "github_repo": "cloud2ai/devify",
        }
    ]
    assert result.external_id == "42"
    assert result.external_url.endswith("/issues/42")
    assert result.metadata["provider"] == "github_issue"
    assert result.metadata["github_repo"] == "cloud2ai/devify"
    assert result.metadata["relay_strategy"] == "update"


@pytest.mark.parametrize(
    ("reference_provider", "reference_repo"),
    [
        ("github_issue", "cloud2ai/old-repo"),
        ("jira", ""),
    ],
)
def test_adapter_creates_new_issue_when_reference_target_changed(
    monkeypatch,
    github_config,
    reference_provider,
    reference_repo,
):
    update_issue = Mock(return_value="42")
    create_issue = Mock(return_value="99")
    monkeypatch.setattr(GitHubIssueHandler, "update_issue", update_issue)
    monkeypatch.setattr(GitHubIssueHandler, "create_issue", create_issue)
    monkeypatch.setattr(
        GitHubIssueHandler,
        "get_issue_url",
        lambda self, issue_number: (
            f"https://github.com/{self.repo}/issues/{issue_number}"
        ),
    )
    event = SimpleNamespace(
        email_message=SimpleNamespace(subject="Original subject"),
        email_message_id=7,
        artifact_snapshot={
            "summary_title": "Updated title",
            "summary_content": "Updated body",
            "attachments": [],
        },
    )
    subscription = SimpleNamespace(
        target_type="github_issue",
        config=github_config,
        strategies={},
    )
    delivery = SimpleNamespace(
        external_id="",
        metadata={
            "relay_delivery_plan": {
                "action": "update",
                "source": "auto_merge",
                "reference_external_id": "42",
                "reference_delivery_id": 1,
                "reference_github_repo": reference_repo,
                "reference_provider": reference_provider,
                "related_issue_keys": ["42"],
                "related_issue_references": (
                    [
                        {
                            "external_id": "42",
                            "provider": "github_issue",
                            "github_repo": reference_repo,
                        }
                    ]
                    if reference_provider == "github_issue"
                    else []
                ),
                "linking_supported": True,
            }
        },
    )

    result = GitHubIssueRelayAdapter().deliver(
        event=event,
        subscription=subscription,
        delivery=delivery,
    )

    update_issue.assert_not_called()
    create_issue.assert_called_once()
    if reference_provider == "github_issue":
        create_email_data = create_issue.call_args.kwargs["email_data"]
        assert create_email_data["related_issue_references"][0]["external_id"] == "42"
    assert result.external_id == "99"
    assert result.external_url == "https://github.com/cloud2ai/devify/issues/99"
    assert result.metadata["github_repo"] == "cloud2ai/devify"


def test_subscription_serializer_validates_github_config_shape(github_config):
    valid = RelaySubscriptionSerializer(
        data={
            "target_type": "github_issue",
            "name": "GitHub",
            "config": github_config,
        }
    )
    assert valid.is_valid(), valid.errors

    invalid = RelaySubscriptionSerializer(
        data={
            "target_type": "github_issue",
            "name": "GitHub",
            "config": {
                "github": {
                    "repo": "cloud2ai/devify",
                    "token": "token",
                    "labels": "relay",
                }
            },
        }
    )
    assert not invalid.is_valid()
    assert "config" in invalid.errors


def test_model_exposes_github_issue_target_choice():
    assert RelaySubscription.TargetType.GITHUB_ISSUE == "github_issue"
