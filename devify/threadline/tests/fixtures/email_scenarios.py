"""
Reusable EmailMessage scenarios for integration and future functional tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from django.utils import timezone

from threadline.models import EmailAttachment, EmailMessage
from threadline.state_machine import EmailStatus

from .factories import EmailAttachmentFactory, EmailMessageFactory


@dataclass(slots=True)
class EmailMessageScenario:
    """A created EmailMessage plus its supporting attachments."""

    email: EmailMessage
    attachments: list[EmailAttachment] = field(default_factory=list)


def create_email_message_scenario(
    user,
    *,
    subject: str = "Subject",
    message_id: str | None = None,
    received_at: datetime | None = None,
    status: str = EmailStatus.FETCHED.value,
    sender: str = "sender@example.com",
    recipients: str = "recipient@example.com",
    text_content: str = "Plain text body",
    html_content: str = "",
    summary_title: str = "",
    summary_content: str = "",
    summary_priority: str = "",
    llm_content: str = "",
    metadata: dict[str, Any] | None = None,
    raw_message_id: str = "",
    in_reply_to: str = "",
    references: list[str] | None = None,
    attachments: list[dict[str, Any]] | None = None,
    **overrides,
) -> EmailMessageScenario:
    """
    Create a standard EmailMessage scenario with optional attachments.

    This is the base building block for integration tests that simulate
    a message already ingested into the system.
    """

    email = EmailMessageFactory(
        user=user,
        subject=subject,
        message_id=message_id or f"<{uuid4()}@example.com>",
        received_at=received_at or timezone.now(),
        status=status,
        sender=sender,
        recipients=recipients,
        text_content=text_content,
        html_content=html_content,
        summary_title=summary_title,
        summary_content=summary_content,
        summary_priority=summary_priority,
        llm_content=llm_content,
        metadata=metadata or {},
        raw_message_id=raw_message_id,
        in_reply_to=in_reply_to,
        references=references or [],
        **overrides,
    )

    created_attachments: list[EmailAttachment] = []
    for attachment_data in attachments or []:
        created_attachments.append(
            EmailAttachmentFactory(
                email_message=email,
                user=user,
                **attachment_data,
            )
        )

    return EmailMessageScenario(email=email, attachments=created_attachments)


def create_merge_pair_scenario(
    user,
    *,
    canonical_subject: str = "Canonical thread",
    child_subject: str = "Canonical thread",
    canonical_text: str = "Canonical body",
    child_text: str = "Child body",
    canonical_received_at: datetime | None = None,
    child_received_at: datetime | None = None,
    merge_reason: str = EmailMessage.MergeReason.MANUAL.value,
) -> tuple[EmailMessage, EmailMessage]:
    """
    Create a canonical/child pair for merge-related tests.
    """

    canonical = create_email_message_scenario(
        user,
        subject=canonical_subject,
        text_content=canonical_text,
        received_at=canonical_received_at or timezone.now(),
    ).email
    child = create_email_message_scenario(
        user,
        subject=child_subject,
        text_content=child_text,
        received_at=child_received_at or timezone.now(),
    ).email
    child.merged_into = canonical
    child.merge_reason = merge_reason
    child.save(update_fields=["merged_into", "merge_reason"])
    return canonical, child


def build_workflow_finalize_state(
    email: EmailMessage,
    *,
    summary_title: str = "Resolved summary title",
    summary_content: str = "Resolved summary content",
    summary_data: dict[str, Any] | None = None,
    llm_content: str = "Resolved llm content",
    metadata: dict[str, Any] | None = None,
    attachments: list[dict[str, Any]] | None = None,
    todos: list[dict[str, Any]] | None = None,
    issue_result_data: dict[str, Any] | None = None,
    issue_id: int | None = None,
    force: bool = False,
    node_errors: dict[str, list[dict[str, Any]]] | None = None,
    credits_consumed: bool = False,
) -> dict[str, Any]:
    """
    Build a workflow finalize state payload for tests.
    """

    attachment_payload = attachments
    if attachment_payload is None:
        attachment_payload = [
            {
                "id": str(att.id),
                "ocr_content": "OCR body",
                "llm_content": "LLM body",
            }
            for att in email.attachments.all()
        ]

    return {
        "id": str(email.id),
        "user_id": str(email.user_id),
        "summary_title": summary_title,
        "summary_content": summary_content,
        "summary_data": summary_data
        if summary_data is not None
        else {"details": ["alpha"], "key_process": ["beta"]},
        "llm_content": llm_content,
        "metadata": metadata if metadata is not None else {"keywords": ["alpha"]},
        "attachments": attachment_payload,
        "todos": todos
        if todos is not None
        else [
            {
                "content": "Follow up with customer",
                "priority": "high",
                "owner": "Alice",
                "deadline_processed": "2026-05-10T08:00:00Z",
                "location": "Shanghai",
                "metadata": {"source": "workflow"},
            }
        ],
        "issue_result_data": issue_result_data
        if issue_result_data is not None
        else {
            "external_id": "REQ-900",
            "issue_url": "https://jira.example.com/browse/REQ-900",
            "title": "Resolved summary title",
            "description": "Resolved summary content",
            "priority": "High",
            "engine": "jira",
            "metadata": {"provider": "jira"},
        },
        "issue_id": issue_id,
        "force": force,
        "node_errors": node_errors if node_errors is not None else {},
        "credits_consumed": credits_consumed,
    }
