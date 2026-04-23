"""
Email Fetch Tasks

Provides unified email fetching tasks for both IMAP and Haraka email sources.

File: devify/threadline/tasks/email_fetch.py
"""

import logging
from typing import Dict

from celery import shared_task
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
from django.db.models import Prefetch

from threadline.models import EmailTask, Settings
from threadline.utils.email import (
    EmailProcessor,
    EmailSaveService,
)
from threadline.utils.task_cleanup import cleanup_stale_tasks
from threadline.utils.task_cleanup import cleanup_old_tasks as cleanup_func
from threadline.utils.task_lock import (
    acquire_task_lock,
    prevent_duplicate_task,
    release_task_lock,
)
from threadline.utils.task_tracer import TaskTracer
from threadline.tasks.email_workflow import process_email_workflow

logger = logging.getLogger(__name__)


@shared_task
@prevent_duplicate_task(
    "imap_email_fetch", timeout=settings.TASK_TIMEOUT_MINUTES
)
def imap_email_fetch():
    """
    IMAP email fetch task

    Responsibilities:
    1. Traverse all active users' IMAP configurations
    2. Process emails for each user independently
    3. Update EmailTask statistics
    4. Use unified email save service
    5. Independent error handling and monitoring
    """
    tracer = TaskTracer("IMAP_EMAIL_FETCH")
    context = tracer.context_summary()

    try:
        task_id = getattr(imap_email_fetch.request, "id", "") or ""
        tracer.set_task_id(task_id)
        tracer.create_task([])
        context = tracer.context_summary()

        logger.info(f"{context} Starting IMAP email fetch task")
        tracer.append_task("INIT", "IMAP email fetch task started")

        # Query users with IMAP configuration
        # Use __contains for MySQL JSONField compatibility
        # This queries for Settings where value contains {"mode": "custom_imap"}
        # and value contains an "imap_config" key
        users_with_imap_config = (
            User.objects.filter(
                is_active=True,
                settings__key="email_config",
                settings__is_active=True,
                settings__value__contains={"mode": "custom_imap"},
            )
            .prefetch_related(
                Prefetch(
                    "settings",
                    queryset=Settings.objects.filter(
                        key="email_config", is_active=True
                    ),
                )
            )
            .distinct()
        )

        processed_count = 0
        error_count = 0
        emails_processed = 0
        email_ids = []

        for user in users_with_imap_config:
            user_display = f"{user.username} (ID: {user.id})"
            try:
                logger.info(f"{context} Processing user {user_display}")
                tracer.append_task(
                    "USER_PROCESS", f"Starting to process user {user_display}"
                )

                email_config_setting = user.settings.first()
                if not email_config_setting:
                    logger.warning(
                        f"{context} User {user_display} has no email_config, skipping"
                    )
                    continue

                email_config = email_config_setting.value

                if "imap_config" not in email_config:
                    logger.warning(
                        f"{context} User {user_display} email_config missing imap_config, skipping"
                    )
                    continue

                # Fetch emails for each user with pre-fetched config
                result = fetch_user_imap_emails(
                    user.id, email_config, user_display=user_display
                )
                processed_count += 1
                emails_processed += result.get("emails_processed", 0)
                email_ids.extend(result.get("email_ids", []))

                tracer.append_task(
                    "USER_SUCCESS",
                    f"User {user_display} processing completed: {result}",
                )

            except Exception as exc:
                error_count += 1
                tracer.append_task(
                    "USER_ERROR",
                    f"User {user_display} processing failed: {str(exc)}",
                    {"level": "ERROR"},
                )
                logger.error(
                    f"{context} Failed to process user {user_display}: {exc}"
                )

        message = (
            f"IMAP email fetch completed: {processed_count} users, "
            f"{error_count} errors"
        )
        tracer.append_task(
            "COMPLETE",
            message,
            {
                "processed_users": processed_count,
                "emails_processed": emails_processed,
                "error_count": error_count,
            },
        )
        tracer.complete_task(tracer.task.details)
        logger.info(f"{context} {message}")

        if email_ids:
            for email_id in email_ids:
                process_email_workflow.delay(email_id)

            logger.info(
                f"{context} Triggered processing for {len(email_ids)} emails: {email_ids}"
            )

        return {
            "processed_users": processed_count,
            "emails_processed": emails_processed,
            "email_ids": email_ids,
            "error_count": error_count,
            "status": "completed",
        }

    except Exception as exc:
        logger.error(f"{context} IMAP email fetch failed: {exc}")
        if tracer.task:
            tracer.fail_task(
                tracer.task.details if tracer.task.details else [], str(exc)
            )
        raise


@shared_task
@prevent_duplicate_task(
    "haraka_email_fetch", timeout=settings.TASK_TIMEOUT_MINUTES
)
def haraka_email_fetch():
    """
    Haraka email fetch task

    Responsibilities:
    1. Fetch all Haraka emails
    2. Filter and assign emails to users based on content
    3. Use unified email save service
    4. Independent error handling and monitoring
    """
    tracer = TaskTracer("HARAKA_EMAIL_FETCH")
    context = tracer.context_summary()

    try:
        task_id = getattr(haraka_email_fetch.request, "id", "") or ""
        tracer.set_task_id(task_id)
        tracer.create_task([])
        context = tracer.context_summary()

        logger.info(f"{context} Starting Haraka email fetch task")
        tracer.append_task("INIT", "Haraka email fetch task started")

        # Create email save service and pre-load user mappings for performance
        save_service = EmailSaveService()
        save_service.load_user_mappings()  # Load all users and aliases once

        # Use existing EmailProcessor to process Haraka emails
        processor = EmailProcessor(source="file", parser_type="flanker")

        processed_count = 0
        error_count = 0
        email_ids = []

        for email_data in processor.process_emails():
            try:
                user = save_service.find_user_by_recipient(email_data)
                if not user:
                    logger.warning(
                        f"{context} No user found for recipients: {email_data.get('recipients')}"
                    )
                    tracer.append_task(
                        "EMAIL_SKIP",
                        (
                            "No user found for recipients: "
                            f"{email_data.get('recipients')}"
                        ),
                        {"level": "WARNING"},
                    )
                    continue

                email_msg = save_service.save_email(user.id, email_data)

                if email_msg is None:
                    logger.info(
                        f"{context} Duplicate email skipped for user {user.username}({user.id}): {email_data['message_id']}"
                    )
                    continue

                processed_count += 1
                email_ids.append(email_msg.id)

                tracer.append_task(
                    "EMAIL_SUCCESS",
                    f"Email saved: {email_msg.id} for user {user.id}",
                )
                logger.info(
                    f"{context} Haraka email saved: email_id={email_msg.id} for user {user.username}({user.id})"
                )

            except Exception as exc:
                error_count += 1
                tracer.append_task(
                    "EMAIL_ERROR",
                    f"Failed to process email: {str(exc)}",
                    {"level": "ERROR"},
                )
                logger.error(f"{context} Failed to process email: {exc}")

        message = (
            f"Haraka email fetch completed: {processed_count} emails, "
            f"{error_count} errors"
        )
        tracer.append_task(
            "COMPLETE",
            message,
            {"emails_processed": processed_count, "error_count": error_count},
        )
        tracer.complete_task(tracer.task.details)
        logger.info(f"{context} {message}")

        if email_ids:
            for email_id in email_ids:
                process_email_workflow.delay(email_id)

            logger.info(
                f"{context} Triggered processing for {len(email_ids)} emails: {email_ids}"
            )

        return {
            "emails_processed": processed_count,
            "email_ids": email_ids,
            "errors": error_count,
            "status": "completed",
        }

    except Exception as exc:
        logger.error(f"{context} Haraka email fetch failed: {exc}")
        if tracer.task:
            tracer.fail_task(
                tracer.task.details if tracer.task.details else [], str(exc)
            )
        raise


@shared_task
@prevent_duplicate_task(
    "fetch_user_imap_emails", lock_param="user_id", timeout=300
)
def fetch_user_imap_emails(
    user_id: int, email_config: dict, user_display: str = None
):
    """
    Fetch IMAP emails for specific user

    Args:
        user_id: User ID
        email_config: Pre-fetched email configuration (required for optimization)
        user_display: User display string for logging (optional, e.g.
                      "admin (ID: 1)")
    """
    if not user_display:
        user_display = f"User ID: {user_id}"
    context = f"[IMAP_FETCH | user_id={user_id}]"

    try:
        if not email_config or "imap_config" not in email_config:
            logger.warning(f"{context} User {user_display} has no IMAP config")
            return {"status": "skipped", "reason": "no_imap_config"}

        imap_config = email_config.get("imap_config", {})
        imap_host = imap_config.get("imap_host", "unknown")
        imap_port = imap_config.get("imap_port", "unknown")
        use_ssl = imap_config.get("use_ssl", True)
        folder = imap_config.get("folder", "INBOX")

        logger.info(
            f"{context} Starting IMAP fetch for {user_display} from {imap_host}:{imap_port} (SSL: {use_ssl}), folder: {folder}"
        )

        processor = EmailProcessor(
            source="imap",
            parser_type="flanker",
            email_config=email_config,
            user_context=user_display,
        )

        save_service = EmailSaveService()
        processed_count = 0
        error_count = 0
        email_ids = []

        for email_data in processor.process_emails():
            try:
                email_msg = save_service.save_email(user_id, email_data)

                if email_msg is None:
                    logger.info(
                        f"{context} Duplicate email skipped for {user_display}: {email_data['message_id']}"
                    )
                    continue

                processed_count += 1
                email_ids.append(email_msg.id)
            except Exception as exc:
                error_count += 1
                logger.error(
                    f"{context} Failed to save email for {user_display}: {exc}"
                )

        result = {
            "emails_processed": processed_count,
            "email_ids": email_ids,
            "errors": error_count,
            "status": "completed",
        }

        logger.info(
            f"{context} IMAP fetch completed for {user_display} from {imap_host}:{imap_port}: {processed_count} emails, {error_count} errors"
        )
        return result

    except Exception as exc:
        logger.error(f"{context} IMAP fetch failed for {user_display}: {exc}")
        raise


@shared_task
def cleanup_old_tasks():
    """
    Periodic task cleanup
    """
    try:
        result = cleanup_func(days_old=1)
        logger.info(f"[TASK_CLEANUP] Task cleanup completed: {result}")
        return result

    except Exception as exc:
        logger.error(f"[TASK_CLEANUP] Task cleanup failed: {exc}")
        raise
