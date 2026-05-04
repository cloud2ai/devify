"""
Compatibility helpers for task-lock cleanup.

Production task locking now lives in agentcore_task.adapters.django.
This module only keeps the small cleanup helper that needs to release all
known lock keys used by Threadline.
"""

from __future__ import annotations

import logging

from django.core.cache import cache

from agentcore_task.adapters.django.services.lock import (
    acquire_task_lock,
    is_task_locked,
    prevent_duplicate_task,
    release_task_lock,
)

logger = logging.getLogger(__name__)


LOCK_KEY_PREFIX = "agentcore_task_task_lock"


def force_release_all_locks():
    """
    Force release all known task locks used by Threadline.
    """
    try:
        all_lock_keys = [
            f"{LOCK_KEY_PREFIX}:email_fetch",
            f"{LOCK_KEY_PREFIX}:imap_email_fetch",
            f"{LOCK_KEY_PREFIX}:haraka_email_fetch",
            f"{LOCK_KEY_PREFIX}:stuck_email_reset",
            f"{LOCK_KEY_PREFIX}:haraka_cleanup",
            f"{LOCK_KEY_PREFIX}:email_task_cleanup",
            f"{LOCK_KEY_PREFIX}:process_email_merge",
            f"{LOCK_KEY_PREFIX}:process_email_workflow",
            f"{LOCK_KEY_PREFIX}:share_link_cleanup",
        ]
        deleted_count = cache.delete_many(all_lock_keys)
        logger.info("Force released %s task locks", deleted_count)
    except Exception as exc:
        logger.error("Failed to force release locks: %s", exc)
