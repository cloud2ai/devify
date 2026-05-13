"""Relay event publishing service."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any, Dict

from django.db import transaction
from django.utils import timezone

from relay.models import RelayEvent

logger = logging.getLogger(__name__)


class RelayEventPublisher:
    """Create relay events and enqueue asynchronous processing."""

    @staticmethod
    def _build_snapshot(state: Dict[str, Any]) -> Dict[str, Any]:
        keys = (
            "summary_title",
            "summary_content",
            "summary_data",
            "llm_content",
            "metadata",
            "todos",
            "attachments",
            "language",
            "scene",
            "subject",
            "trigger_source",
        )
        snapshot = {key: state.get(key) for key in keys if state.get(key) is not None}
        attachments = state.get("attachments")
        if attachments:
            snapshot["attachments"] = [
                dict(attachment)
                if isinstance(attachment, Mapping)
                else attachment
                for attachment in attachments
            ]
            snapshot["attachment_count"] = len(attachments)
        snapshot["source_state"] = {
            "email_id": state.get("id"),
            "user_id": state.get("user_id"),
        }
        return snapshot

    @classmethod
    def publish_workflow_completed(cls, *, email, state: Dict[str, Any]) -> RelayEvent:
        snapshot = cls._build_snapshot(state)
        event = RelayEvent.objects.create(
            user=email.user,
            email_message=email,
            event_type=RelayEvent.EventType.WORKFLOW_COMPLETED,
            artifact_snapshot=snapshot,
            status=RelayEvent.Status.PENDING,
        )

        def _enqueue():
            from relay.tasks import process_relay_event

            try:
                process_relay_event.delay(str(event.id))
                logger.info("Queued relay event %s for delivery", event.id)
            except Exception:
                logger.exception(
                    "Failed to enqueue relay event %s; event remains PENDING",
                    event.id,
                )

        transaction.on_commit(_enqueue)
        return event
