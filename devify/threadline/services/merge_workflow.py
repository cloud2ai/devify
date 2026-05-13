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
    Enqueue the merge workflow and surface processing status immediately.

    Mark the target record as PROCESSING before queueing the workflow so the
    detail page reflects that work is already in progress instead of waiting
    for the Celery worker to start.
    """
    from threadline.tasks.email_merge import process_email_merge

    target_message = message

    try:
        if target_message.status != EmailStatus.PROCESSING.value:
            target_message.set_status(EmailStatus.PROCESSING.value)
        target_message.set_processing_progress(0)

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


def enqueue_merge_workflows(
    messages: list[EmailMessage],
    *,
    force: bool = False,
    language: str | None = None,
    scene: str | None = None,
    trigger_source: str = "unknown",
) -> list[dict]:
    """
    Enqueue merge workflows for multiple messages and collect per-item results.
    """
    results: list[dict] = []

    for message in messages:
        try:
            target_message = enqueue_merge_workflow(
                message,
                force=force,
                language=language,
                scene=scene,
                trigger_source=trigger_source,
            )
            results.append(
                {
                    "requested_email_id": str(message.id),
                    "requested_uuid": str(message.uuid),
                    "email_id": str(target_message.id),
                    "uuid": str(target_message.uuid),
                    "status": "success",
                }
            )
        except Exception as exc:
            results.append(
                {
                    "requested_email_id": str(message.id),
                    "requested_uuid": str(message.uuid),
                    "email_id": str(message.id),
                    "uuid": str(message.uuid),
                    "status": "failed",
                    "error": str(exc),
                }
            )

    return results
