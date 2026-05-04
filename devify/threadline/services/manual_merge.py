"""
Manual email merge service.

This service creates a new canonical EmailMessage from a small selection of
existing messages, copies their attachments, and links the source messages to
the new canonical record.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import uuid4

from django.db import transaction
from django.utils import timezone

from threadline.models import EmailAttachment, EmailMessage

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ManualMergeResult:
    canonical_message: EmailMessage
    source_messages: list[EmailMessage]
    attachment_count: int


class ManualMergeService:
    """
    Service for manually merging a small batch of email messages.
    """

    def _build_merge_note_block(self, merge_note: str | None) -> str:
        """
        Build a short top-of-body note for the canonical text content.
        """
        cleaned_note = (merge_note or "").strip()
        if not cleaned_note:
            return ""

        return "\n".join(
            [
                "[Manual merge note]",
                cleaned_note,
            ]
        ).strip()

    def _build_merged_text(self, messages: list[EmailMessage]) -> str:
        """
        Build a structured plain-text body from the source messages.
        """
        sections: list[str] = []

        for index, message in enumerate(messages, start=1):
            lines: list[str] = [
                f"[Source {index}]",
                f"Subject: {message.subject or '(No Subject)'}",
                f"Sender: {message.sender or ''}",
                f"Recipients: {message.recipients or ''}",
                f"Received at: {message.received_at.isoformat()}",
            ]

            if message.text_content:
                lines.append("")
                lines.append(message.text_content.strip())

            attachment_names = [
                attachment.filename
                for attachment in message.attachments.all().order_by("id")
            ]
            if attachment_names:
                lines.append("")
                lines.append("Attachments:")
                lines.extend(f"- {name}" for name in attachment_names)

            sections.append("\n".join(lines).strip())

        return "\n\n---\n\n".join(sections).strip()

    def _clone_attachments(
        self,
        source_messages: list[EmailMessage],
        canonical_message: EmailMessage,
    ) -> int:
        """
        Copy attachment rows to the canonical message.
        """
        created_count = 0

        for source in source_messages:
            attachments = source.attachments.all().order_by("id")
            for attachment in attachments:
                EmailAttachment.objects.create(
                    user=canonical_message.user,
                    email_message=canonical_message,
                    filename=attachment.filename,
                    safe_filename=attachment.safe_filename,
                    content_type=attachment.content_type,
                    file_size=attachment.file_size,
                    file_path=attachment.file_path,
                    content_md5=attachment.content_md5,
                    is_image=attachment.is_image,
                    ocr_content=attachment.ocr_content,
                    llm_content=attachment.llm_content,
                )
                created_count += 1

        return created_count

    @transaction.atomic
    def merge(
        self,
        *,
        user,
        source_messages: list[EmailMessage],
        merge_note: str | None = None,
    ) -> ManualMergeResult:
        """
        Create a canonical message from the provided source messages.
        """
        if len(source_messages) < 2:
            raise ValueError("At least two messages are required to merge")
        if len(source_messages) > 5:
            raise ValueError("You can merge at most five messages at once")

        ordered_sources = sorted(
            source_messages,
            key=lambda message: (message.received_at, message.id),
        )
        canonical_source = ordered_sources[0]
        merged_text = self._build_merged_text(ordered_sources)
        merge_note_block = self._build_merge_note_block(merge_note)
        if merge_note_block:
            merged_text = "\n\n---\n\n".join(
                [merge_note_block, merged_text]
            ).strip()
        merged_at = timezone.now()

        canonical_message = EmailMessage.objects.create(
            user=user,
            message_id=f"manual-merge-{uuid4().hex}",
            subject=canonical_source.subject or "(No Subject)",
            sender=canonical_source.sender,
            recipients=canonical_source.recipients,
            # Treat the manual merge as a fresh record so it sorts to the top.
            received_at=merged_at,
            text_content=merged_text,
            html_content="",
            metadata={
                "manual_merge": {
                    "source_count": len(ordered_sources),
                    "source_ids": [message.id for message in ordered_sources],
                    "source_uuids": [
                        str(message.uuid) for message in ordered_sources
                    ],
                    "merged_at": merged_at.isoformat(),
                }
            },
        )

        attachment_count = self._clone_attachments(
            ordered_sources, canonical_message
        )

        for source in ordered_sources:
            source.merged_into = canonical_message
            source.merge_reason = EmailMessage.MergeReason.MANUAL.value
            source.last_merged_at = merged_at
            source.save(
                update_fields=["merged_into", "merge_reason", "last_merged_at"]
            )

        canonical_message.refresh_from_db()

        logger.info(
            "Manual merge created canonical message %s from %s sources",
            canonical_message.uuid,
            len(ordered_sources),
        )

        return ManualMergeResult(
            canonical_message=canonical_message,
            source_messages=ordered_sources,
            attachment_count=attachment_count,
        )
