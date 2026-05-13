from types import SimpleNamespace
from uuid import uuid4

import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model

from threadline.agents.nodes.workflow_prepare import WorkflowPrepareNode
from threadline.models import EmailMessage, Issue
from threadline.state_machine import EmailStatus

User = get_user_model()


class _RelatedSet:
    def __init__(self, items=None):
        self._items = list(items or [])

    def all(self):
        return list(self._items)


def _build_email(**kwargs):
    user = SimpleNamespace(id=2, profile=None)
    defaults = {
        "id": 1,
        "user_id": user.id,
        "user": user,
        "uuid": uuid4(),
        "message_id": "<message@example.com>",
        "subject": "Subject",
        "sender": "sender@example.com",
        "recipients": "recipient@example.com",
        "received_at": None,
        "html_content": "",
        "text_content": "",
        "summary_title": None,
        "summary_content": None,
        "summary_data": None,
        "llm_content": None,
        "metadata": None,
        "created_at": None,
        "updated_at": None,
        "merged_into_id": None,
        "merged_into": None,
        "merged_children": _RelatedSet(),
        "merge_reason": "",
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_build_email_state_preserves_business_metadata_for_normal_email():
    node = WorkflowPrepareNode()
    node.email = _build_email(metadata={"keywords": ["alpha"]})

    state = node._build_email_state(
        state={},
        prompt_config={},
        issue_config={},
        max_attachments=None,
        attachments_data=[],
        issue_id=None,
        issue_url=None,
        issue_metadata=None,
        issue_result_data=None,
        related_issue_keys=[],
        summary_data=None,
        todos_data=[],
    )

    assert state["metadata"] == {"keywords": ["alpha"]}
    assert state["issue_id"] is None
    assert state["issue_result_data"] is None


def test_strip_runtime_metadata_removes_processing_progress():
    node = WorkflowPrepareNode()

    cleaned = node._strip_runtime_metadata(
        {
            "processing_progress": {"percent": 20},
            "keywords": ["alpha"],
        }
    )

    assert cleaned == {"keywords": ["alpha"]}


def test_build_email_state_clears_metadata_for_child_email():
    canonical = _build_email(
        id=10,
        subject="Canonical",
    )
    child = _build_email(
        id=11,
        merged_into_id=10,
        merged_into=canonical,
        merge_reason="manual",
    )
    canonical.merged_children = _RelatedSet([child])

    node = WorkflowPrepareNode()
    node.email = child

    state = node._build_email_state(
        state={},
        prompt_config={},
        issue_config={
            "auto_merge_strategy": "update",
            "manual_merge_strategy": "linked",
        },
        max_attachments=None,
        attachments_data=[],
        issue_id=None,
        issue_url=None,
        issue_metadata=None,
        issue_result_data=None,
        related_issue_keys=[],
        summary_data=None,
        todos_data=[],
    )

    assert state["metadata"] is None
    assert state["issue_id"] is None
    assert state["issue_result_data"] is None


class TestWorkflowPrepareIssueMetadata(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="workflow-prepare-user",
            email="workflow-prepare-user@example.com",
            password="password",
        )

    def _create_email(self, **kwargs):
        defaults = {
            "user": self.user,
            "message_id": f"<{uuid4()}@example.com>",
            "subject": "Subject",
            "sender": "sender@example.com",
            "recipients": "recipient@example.com",
            "received_at": "2026-05-07T00:00:00Z",
            "html_content": "",
            "text_content": "",
            "status": EmailStatus.FETCHED.value,
        }
        defaults.update(kwargs)
        return EmailMessage.objects.create(**defaults)

    def test_retry_update_reuses_direct_issue(self):
        email = self._create_email()
        issue = Issue.objects.create(
            user=self.user,
            email_message=email,
            external_id="REQ-123",
            engine="jira",
            title="Retry source",
            description="Retry body",
            priority="Medium",
            issue_url="https://jira.example.com/browse/REQ-123",
            metadata={},
        )

        node = WorkflowPrepareNode()
        node.email = email

        issue_id, issue_url, issue_metadata, issue_result_data = (
            node._load_existing_issue_metadata(
                {"retry_issue_strategy": "update"},
                trigger_source="retry_task",
            )
        )

        assert issue_id == issue.id
        assert issue_url == issue.issue_url
        assert issue_metadata["external_id"] == "REQ-123"
        assert issue_result_data["reuse_existing_issue"] is True
        assert issue_result_data["metadata"] == {}

    def test_retry_update_reuses_direct_issue_for_api_retry(self):
        """Test retry via api_retry reuses existing issue"""
        email = self._create_email()
        issue = Issue.objects.create(
            user=self.user,
            email_message=email,
            external_id="REQ-124",
            engine="jira",
            title="Retry source",
            description="Retry body",
            priority="Medium",
            issue_url="https://jira.example.com/browse/REQ-124",
            metadata={},
        )

        node = WorkflowPrepareNode()
        node.email = email

        issue_id, issue_url, issue_metadata, issue_result_data = (
            node._load_existing_issue_metadata(
                {"retry_issue_strategy": "update"},
                trigger_source="api_retry",
            )
        )

        assert issue_id == issue.id
        assert issue_url == issue.issue_url
        assert issue_metadata["external_id"] == "REQ-124"
        assert issue_result_data["reuse_existing_issue"] is True
        assert issue_result_data["metadata"] == {}

    def test_auto_update_uses_canonical_issue_for_merged_child(self):
        canonical = self._create_email()
        child = self._create_email()
        child.merged_into = canonical
        child.save(update_fields=["merged_into"])
        issue = Issue.objects.create(
            user=self.user,
            email_message=canonical,
            external_id="REQ-789",
            engine="jira",
            title="Canonical issue",
            description="Canonical body",
            priority="Medium",
            issue_url="https://jira.example.com/browse/REQ-789",
            metadata={},
        )

        node = WorkflowPrepareNode()
        node.email = child

        issue_id, issue_url, issue_metadata, issue_result_data = (
            node._load_existing_issue_metadata(
                {"auto_merge_strategy": "update"},
                trigger_source=None,
            )
        )

        assert issue_id == issue.id
        assert issue_url == issue.issue_url
        assert issue_metadata["external_id"] == "REQ-789"
        assert issue_result_data["reuse_existing_issue"] is True
        assert issue_result_data["metadata"] == {}

    def test_retry_new_ignores_existing_issue(self):
        email = self._create_email()
        Issue.objects.create(
            user=self.user,
            email_message=email,
            external_id="REQ-456",
            engine="jira",
            title="Retry source",
            description="Retry body",
            priority="Medium",
            issue_url="https://jira.example.com/browse/REQ-456",
            metadata={},
        )

        node = WorkflowPrepareNode()
        node.email = email

        issue_id, issue_url, issue_metadata, issue_result_data = (
            node._load_existing_issue_metadata(
                {"retry_issue_strategy": "new"},
                trigger_source="retry_task",
            )
        )

        assert issue_id is None
        assert issue_url is None
        assert issue_metadata is None
        assert issue_result_data is None
