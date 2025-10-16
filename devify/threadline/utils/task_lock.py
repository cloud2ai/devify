"""
Task Lock Management

Provides utilities for managing task locks to prevent
duplicate execution.
"""

import logging
from typing import Optional
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


def acquire_task_lock(
    lock_name: str,
    timeout: int = settings.TASK_TIMEOUT_MINUTES
) -> bool:
    """
    Acquire task lock

    Args:
        lock_name: Lock name
            (e.g., 'email_fetch', 'imap_email_fetch')
        timeout: Lock timeout in minutes
            (default: from TASK_TIMEOUT_MINUTES setting)

    Returns:
        True if lock acquired successfully, False if already locked
    """
    lock_key = f"email_fetch_lock:{lock_name}"

    try:
        # Try to acquire lock with timeout
        acquired = cache.add(lock_key, "locked", timeout=timeout)

        if acquired:
            logger.info(f"Acquired task lock: {lock_name}")
        else:
            logger.warning(f"Task lock already exists: {lock_name}")

        return acquired

    except Exception as exc:
        logger.error(f"Failed to acquire task lock {lock_name}: {exc}")
        return False


def release_task_lock(lock_name: str) -> bool:
    """
    Release task lock

    Args:
        lock_name: Lock name to release

    Returns:
        True if lock released successfully
    """
    lock_key = f"email_fetch_lock:{lock_name}"

    try:
        cache.delete(lock_key)
        logger.info(f"Released task lock: {lock_name}")
        return True

    except Exception as exc:
        logger.error(f"Failed to release task lock {lock_name}: {exc}")
        return False


def is_task_locked(lock_name: str) -> bool:
    """
    Check if task is locked

    Args:
        lock_name: Lock name to check

    Returns:
        True if task is locked
    """
    lock_key = f"email_fetch_lock:{lock_name}"

    try:
        return cache.get(lock_key) is not None

    except Exception as exc:
        logger.error(f"Failed to check task lock {lock_name}: {exc}")
        return False


def force_release_all_locks():
    """
    Force release all email fetch locks (for cleanup)
    """
    try:
        from django.core.cache import cache

        # Define all possible lock keys
        all_lock_keys = [
            'email_fetch_lock:email_fetch',
            'email_fetch_lock:imap_email_fetch',
            'email_fetch_lock:haraka_email_fetch',
            'email_fetch_lock:stuck_email_reset',
            'email_fetch_lock:haraka_cleanup',
            'email_fetch_lock:email_task_cleanup'
        ]

        # Batch delete all locks
        deleted_count = cache.delete_many(all_lock_keys)
        logger.info(f"Force released {deleted_count} task locks")

    except Exception as exc:
        logger.error(f"Failed to force release locks: {exc}")


def prevent_duplicate_task(
    lock_name: str,
    timeout: int = settings.TASK_TIMEOUT_MINUTES,
    lock_param: str = None
):
    """
    Decorator to prevent duplicate task execution

    Args:
        lock_name: Base lock name for the task
        timeout: Lock timeout in seconds
        lock_param: Parameter name to use for generating unique lock
            (e.g., 'email_id', 'user_id', 'task_id')
            If provided, the lock name will be: {lock_name}_{param_value}
            If not provided, all tasks share the same lock

    Examples:
        # Single global lock for the task
        @prevent_duplicate_task("email_fetch")
        def fetch_emails():
            pass

        # Per-user lock
        @prevent_duplicate_task("fetch_user_emails", lock_param="user_id")
        def fetch_user_emails(user_id):
            pass

        # Per-email lock
        @prevent_duplicate_task("process_email", lock_param="email_id")
        def process_email(email_id, force=False):
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Build lock name
            task_lock_name = lock_name

            if lock_param:
                # Try to get parameter value from kwargs first,
                # then from args[0]
                param_value = kwargs.get(lock_param) or (
                    args[0] if args else None
                )

                if param_value:
                    task_lock_name = f"{lock_name}_{param_value}"
                    logger.debug(
                        f"Built lock name with {lock_param}={param_value}: "
                        f"{task_lock_name}"
                    )
                else:
                    logger.warning(
                        f"Could not extract {lock_param} from task "
                        f"arguments, using base lock name: {lock_name}"
                    )

            # Check if task is already running
            if is_task_locked(task_lock_name):
                logger.warning(
                    f"Task {task_lock_name} is already running, skipping"
                )
                return {
                    'status': 'skipped',
                    'reason': 'task_already_running'
                }

            # Acquire lock
            if not acquire_task_lock(task_lock_name, timeout):
                logger.warning(
                    f"Failed to acquire lock for {task_lock_name}"
                )
                return {
                    'status': 'skipped',
                    'reason': 'lock_acquisition_failed'
                }

            try:
                # Execute task
                result = func(*args, **kwargs)
                return result

            finally:
                # Always release lock
                release_task_lock(task_lock_name)

        # Preserve original function attributes
        wrapper.__name__ = func.__name__
        wrapper.__module__ = func.__module__
        wrapper.__doc__ = func.__doc__

        return wrapper
    return decorator
