"""
Startup recovery helpers for Threadline email processing.

These helpers run when a Celery worker becomes ready. They recover stale
processing records that were likely left behind by a worker crash or restart.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from agentcore_task.adapters.django import acquire_task_lock, release_task_lock
from threadline.models import EmailMessage
from threadline.state_machine import EmailStatus
from threadline.tasks.email_merge import process_email_merge

logger = logging.getLogger(__name__)


STARTUP_RECOVERY_LOCK_NAME = "threadline_startup_recovery"


def recover_stuck_processing_emails(
    *,
    timeout_minutes: int | None = None,
) -> dict:
    """
    Requeue stale processing emails after a worker restart.

    The recovery is intentionally conservative:
    - Only EmailMessage rows in PROCESSING state are considered.
    - Only rows older than the timeout window are recovered.
    - A distributed lock ensures only one worker performs recovery.

    Returns:
        dict: Recovery statistics.
    """
    timeout_minutes = timeout_minutes or settings.TASK_TIMEOUT_MINUTES
    lock_timeout = max(timeout_minutes, 5) * 60

    if not acquire_task_lock(
        STARTUP_RECOVERY_LOCK_NAME,
        timeout=lock_timeout,
    ):
        logger.info(
            "Skipping startup recovery because another worker holds the lock"
        )
        return {
            "status": "skipped",
            "reason": "startup_recovery_lock_exists",
            "timeout_minutes": timeout_minutes,
            "requeued_count": 0,
            "candidate_count": 0,
        }

    try:
        now = timezone.now()
        timeout_threshold = now - timedelta(minutes=timeout_minutes)

        candidates = list(
            EmailMessage.objects.filter(
                status=EmailStatus.PROCESSING.value,
                updated_at__lt=timeout_threshold,
            )
            .select_related("user")
            .order_by("updated_at", "id")
        )

        requeued_count = 0
        dispatch_errors = []

        for email in candidates:
            try:
                process_email_merge.delay(
                    str(email.id),
                    force=False,
                    trigger_source="startup_recovery",
                )
                requeued_count += 1
                logger.info(
                    "Recovered stale processing email %s (%s) "
                    "trigger_source=startup_recovery",
                    email.id,
                    email.uuid,
                )
            except Exception as exc:
                logger.exception(
                    "Failed to requeue stale processing email %s: %s",
                    email.id,
                    exc,
                )
                dispatch_errors.append(
                    {
                        "email_id": str(email.id),
                        "uuid": str(email.uuid),
                        "error": str(exc),
                    }
                )

        return {
            "status": "success",
            "timeout_minutes": timeout_minutes,
            "timeout_threshold": timeout_threshold.isoformat(),
            "candidate_count": len(candidates),
            "requeued_count": requeued_count,
            "dispatch_errors": dispatch_errors,
        }

    finally:
        release_task_lock(STARTUP_RECOVERY_LOCK_NAME)
