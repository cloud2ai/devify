"""
Helpers for triggering the email merge workflow.
"""

from __future__ import annotations

import logging

from threadline.models import EmailMessage, EmailStatus

logger = logging.getLogger(__name__)


def enqueue_merge_workflow(
    message: EmailMessage,
    *,
    force: bool = False,
    language: str | None = None,
    scene: str | None = None,
    trigger_source: str = "unknown",
) -> EmailMessage:
    """
    Mark a message as processing and enqueue the merge workflow.
    """
    from threadline.tasks.email_merge import process_email_merge

    target_message = message
    target_message.set_status(EmailStatus.PROCESSING.value)

    try:
        process_email_merge.delay(
            str(target_message.id),
            force=force,
            language=language,
            scene=scene,
            trigger_source=trigger_source,
        )
    except Exception as exc:
        logger.error(
            "Failed to trigger merge workflow for email %s "
            "trigger_source=%s: %s",
            target_message.uuid,
            trigger_source,
            exc,
        )
        try:
            target_message.set_status(
                EmailStatus.FAILED.value,
                error_message=str(exc),
            )
        except Exception as status_error:
            logger.error(
                "Failed to mark email %s as FAILED after dispatch error: %s",
                target_message.uuid,
                status_error,
            )
        raise

    return target_message
