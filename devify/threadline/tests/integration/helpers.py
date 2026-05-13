"""
Shared helpers for integration tests.

These helpers keep integration cases focused on the business flow:
- create the threadline through the public API
- drive follow-up processing through commands
- temporarily fake external boundaries only inside the test process
"""

from __future__ import annotations

from contextlib import contextmanager, ExitStack
from unittest.mock import Mock, patch
from uuid import uuid4

from django.urls import reverse
from rest_framework.test import APIClient

from core.tracking import LLMTracker
from threadline.models import EmailMessage
from threadline.tests.fixtures.payloads import build_threadline_payload


class FakeIssueHandler:
    """Small fake issue handler for integration tests."""

    def __init__(self, issue_key: str = "REQ-9001"):
        self.issue_key = issue_key
        self.create_issue = Mock(return_value=issue_key)
        self.update_issue = Mock(return_value=issue_key)
        self.upload_attachments = Mock(
            side_effect=self._upload_attachments
        )
        self.get_issue_url = Mock(
            return_value=f"https://jira.example.com/browse/{issue_key}"
        )
        self.link_issue = Mock(return_value=True)
        self.link_related_issues = Mock(
            return_value={"linked_count": 1, "skipped_count": 0}
        )

    @staticmethod
    def _attachment_keys(attachment):
        keys = []
        content_md5 = str(attachment.get("content_md5") or "").strip()
        if content_md5:
            keys.append(f"md5:{content_md5}")

        attachment_id = attachment.get("id")
        if attachment_id not in (None, ""):
            keys.append(f"id:{attachment_id}")

        filename = str(attachment.get("filename") or "unknown").strip()
        file_size = attachment.get("file_size", "")
        keys.append(f"name:{filename}:{file_size}")
        return list(dict.fromkeys(keys))

    def _upload_attachments(self, issue_key, attachments):
        attachments = attachments or []
        uploaded_keys = []
        for item in attachments:
            uploaded_keys.extend(self._attachment_keys(item))
        return {
            "uploaded_count": len(attachments),
            "skipped_count": 0,
            "uploaded_attachment_keys": list(dict.fromkeys(uploaded_keys)),
            "skipped_attachment_keys": [],
        }


def _build_fake_llm_responses():
    summary_json = {
        "details": "Resolved summary details",
        "key_process": ["Confirm requirement", "Create issue"],
        "todos": [
            {
                "content": "Follow up with customer",
                "priority": "high",
                "owner": "Admin",
                "deadline": "2026-05-10",
                "location": "Shanghai",
            }
        ],
    }

    metadata_json = {
        "keywords": ["integration", "issue", "workflow"],
        "participants": ["Admin"],
        "locations": ["Shanghai"],
        "timeline": [],
    }

    def fake_call_and_track(
        prompt,
        content=None,
        json_mode=False,
        max_retries=0,
        state=None,
        node_name="unknown",
        model_uuid=None,
    ):
        if node_name == "llm_email_node":
            response = "Processed email body for workflow"
        elif node_name == "summary_node" and json_mode:
            response = summary_json
        elif node_name == "summary_node":
            response = "Resolved summary title"
        elif node_name == "metadata_node":
            response = metadata_json
        else:
            response = "Generic LLM response"

        usage = {
            "model": "fake-model",
            "prompt_tokens": 1,
            "completion_tokens": 1,
            "total_tokens": 2,
        }
        return response, usage

    def fake_call_messages_and_track(
        messages,
        json_mode=False,
        max_retries=0,
        state=None,
        node_name="unknown",
        model_uuid=None,
    ):
        return fake_call_and_track(
            prompt="",
            content="",
            json_mode=json_mode,
            max_retries=max_retries,
            state=state,
            node_name=node_name,
            model_uuid=model_uuid,
        )

    return fake_call_and_track, fake_call_messages_and_track


@contextmanager
def patched_email_workflow_boundaries(
    *,
    issue_key: str = "REQ-9001",
):
    """
    Patch the workflow's external boundaries inside the current process.
    """

    fake_call_and_track, fake_call_messages_and_track = _build_fake_llm_responses()
    fake_issue_handler = FakeIssueHandler(issue_key=issue_key)

    with ExitStack() as stack:
        stack.enter_context(
            patch("threadline.agents.workflow.create_checkpointer", return_value=None)
        )
        stack.enter_context(
            patch.object(
                LLMTracker,
                "call_and_track",
                side_effect=fake_call_and_track,
            )
        )
        stack.enter_context(
            patch.object(
                LLMTracker,
                "call_messages_and_track",
                side_effect=fake_call_messages_and_track,
            )
        )
        yield fake_issue_handler


def create_threadline_via_api(user, **overrides) -> EmailMessage:
    """
    Create a threadline through the public API and reuse the live DB.
    """

    client = APIClient()
    client.force_authenticate(user=user)
    if "message_id" not in overrides:
        overrides["message_id"] = f"integration-{uuid4()}@example.com"
    payload = build_threadline_payload(**overrides)
    allowed_fields = {
        "user_id",
        "task_id",
        "message_id",
        "subject",
        "sender",
        "recipients",
        "received_at",
        "raw_content",
        "html_content",
        "text_content",
        "raw_message_id",
        "in_reply_to",
        "references",
    }
    payload = {key: value for key, value in payload.items() if key in allowed_fields}

    with patch(
        "threadline.views.email_message._enqueue_merge_workflow",
        side_effect=lambda message, **kwargs: message,
    ):
        response = client.post(reverse("threadlines-list"), payload, format="json")

    if response.status_code not in (200, 201):
        raise AssertionError(f"Failed to create threadline: {response.data}")

    email_id = response.data["data"]["id"]
    return EmailMessage.objects.get(id=email_id)
