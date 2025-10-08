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
from threadline.utils.task_lock import (
    acquire_task_lock,
    prevent_duplicate_task,
    release_task_lock
)
from threadline.utils.task_tracer import TaskTracer

logger = logging.getLogger(__name__)



@shared_task
@prevent_duplicate_task(
    "imap_email_fetch",
    timeout=settings.TASK_TIMEOUT_MINUTES
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
    tracer = TaskTracer('IMAP_EMAIL_FETCH')

    try:
        logger.info("Starting IMAP email fetch task")

        # Create email fetch task record
        task_id = getattr(imap_email_fetch.request, "id", "") or ""
        tracer.create_task([])
        tracer.set_task_id(task_id)
        tracer.append_task("INIT", "IMAP email fetch task started")

        users_with_email_config = User.objects.filter(
            is_active=True,
            settings__key="email_config",
            settings__is_active=True
        ).prefetch_related(
            Prefetch('settings', queryset=Settings.objects.filter(
                key="email_config",
                is_active=True
            ))
        ).distinct()

        processed_count = 0
        error_count = 0
        emails_processed = 0

        for user in users_with_email_config:
            try:
                tracer.append_task(
                    "USER_PROCESS", f"Starting to process user {user.id}")

                # Get email config from prefetched settings (guaranteed
                # to exist)
                email_config_setting = user.settings.first()
                email_config = email_config_setting.value

                # Only check if IMAP config exists (since we already filtered
                # for email_config)
                if "imap_config" not in email_config:
                    logger.debug(f"User {user.id} has no IMAP config, skipping")
                    tracer.append_task(
                        "USER_SKIP",
                        f"User {user.id} has no IMAP config, skipping")
                    continue

                # Fetch emails for each user with pre-fetched config
                result = fetch_user_imap_emails(user.id, email_config)
                processed_count += 1
                emails_processed += result.get("emails_processed", 0)

                tracer.append_task(
                    "USER_SUCCESS",
                    f"User {user.id} processing completed: {result}")

            except Exception as exc:
                error_count += 1
                tracer.append_task(
                    "USER_ERROR",
                    f"User {user.id} processing failed: {str(exc)}",
                    {"level": "ERROR"})
                logger.error(f"Failed to process user {user.id}: {exc}")

        # Complete task
        message = (
            f"IMAP email fetch completed: {processed_count} users, "
            f"{error_count} errors"
        )
        tracer.append_task("COMPLETE", message, {
            'processed_users': processed_count,
            'emails_processed': emails_processed,
            'error_count': error_count
        })
        tracer.complete_task(tracer.task.details)
        logger.info(message)

        return {
            "processed_users": processed_count,
            "emails_processed": emails_processed,
            "error_count": error_count,
            "status": "completed"
        }

    except Exception as exc:
        logger.error(f"IMAP email fetch failed: {exc}")
        if tracer.task:
            tracer.fail_task(
                tracer.task.details if tracer.task.details else [],
                str(exc)
            )
        raise


@shared_task
@prevent_duplicate_task("haraka_email_fetch",
                        timeout=settings.TASK_TIMEOUT_MINUTES)
def haraka_email_fetch():
    """
    Haraka email fetch task

    Responsibilities:
    1. Fetch all Haraka emails
    2. Filter and assign emails to users based on content
    3. Use unified email save service
    4. Independent error handling and monitoring
    """
    tracer = TaskTracer('HARAKA_EMAIL_FETCH')

    try:
        logger.info("Starting Haraka email fetch task")

        # Create email fetch task record
        task_id = getattr(haraka_email_fetch.request, "id", "") or ""
        tracer.create_task([])
        tracer.set_task_id(task_id)
        tracer.append_task("INIT", "Haraka email fetch task started")

        # Create email save service and pre-load user mappings for performance
        save_service = EmailSaveService()
        save_service.load_user_mappings()  # Load all users and aliases once

        # Use existing EmailProcessor to process Haraka emails
        processor = EmailProcessor(
            source="file",
            parser_type="flanker"
        )

        processed_count = 0
        error_count = 0

        # Process all Haraka emails (global processing, auto-assign users)
        for email_data in processor.process_emails():
            try:
                # Find corresponding user based on email recipient info
                user = save_service.find_user_by_recipient(email_data)
                if not user:
                    logger.warning(
                        f"No user found for email recipient: "
                        f"{email_data.get("recipients")}"
                    )
                    # Add execution log for skipped email due to no user found
                    tracer.append_task(
                        "EMAIL_SKIP",
                        (
                            "No user found for recipients: "
                            f"{email_data.get('recipients')}"
                        ),
                        {"level": "WARNING"}
                    )
                    continue

                # Save email directly to corresponding user
                email_msg = save_service.save_email(
                    user.id,
                    email_data,
                    task_id=tracer.task_id
                )
                processed_count += 1

                tracer.append_task(
                    "EMAIL_SUCCESS",
                    f"Email saved: {email_msg.id} for user {user.id}"
                )
                logger.info(
                    f"Haraka email saved: {email_msg.id} "
                    f"for user {user.id}"
                )

            except Exception as exc:
                error_count += 1
                tracer.append_task(
                    "EMAIL_ERROR",
                    f"Failed to process email: {str(exc)}",
                    {"level": "ERROR"}
                )
                logger.error(f"Failed to process Haraka email: {exc}")

        # Complete task
        message = (
            f"Haraka email fetch completed: {processed_count} emails, "
            f"{error_count} errors"
        )
        tracer.append_task("COMPLETE", message, {
            'emails_processed': processed_count,
            'error_count': error_count
        })
        tracer.complete_task(tracer.task.details)
        logger.info(message)

        return {
            "emails_processed": processed_count,
            "errors": error_count,
            "status": "completed"
        }

    except Exception as exc:
        logger.error(f"Haraka email fetch failed: {exc}")
        if tracer.task:
            tracer.fail_task(
                tracer.task.details if tracer.task.details else [],
                str(exc)
            )
        raise


@shared_task
@prevent_duplicate_task(
    "fetch_user_imap_emails",
    user_id_param="user_id",
    timeout=300
)
def fetch_user_imap_emails(user_id: int, email_config: dict):
    """
    Fetch IMAP emails for specific user

    Args:
        user_id: User ID
        email_config: Pre-fetched email configuration (required for optimization)
    """
    try:
        # Validate email config
        if not email_config or "imap_config" not in email_config:
            logger.warning(f"User {user_id} has no IMAP config")
            return {"status": "skipped", "reason": "no_imap_config"}

        # Use existing EmailProcessor to process emails
        processor = EmailProcessor(
            source="imap",
            parser_type="flanker",
            email_config=email_config["imap_config"]
        )

        save_service = EmailSaveService()
        processed_count = 0
        error_count = 0

        # Process emails
        for email_data in processor.process_emails():
            try:
                # Save email to database
                save_service.save_email(user_id, email_data)
                processed_count += 1
            except Exception as exc:
                error_count += 1
                logger.error(f"Failed to save email: {exc}")

        result = {
            "emails_processed": processed_count,
            "errors": error_count,
            "status": "completed"
        }

        logger.info(f"IMAP email fetch completed for user {user_id}: {result}")
        return result

    except Exception as exc:
        logger.error(f"IMAP email fetch failed for user {user_id}: {exc}")
        raise


@shared_task
def cleanup_old_tasks():
    """
    Periodic task cleanup
    """
    try:
        from threadline.utils.task_cleanup import cleanup_old_tasks as cleanup_func
        result = cleanup_func(days_old=1)
        logger.info(f"Task cleanup completed: {result}")
        return result

    except Exception as exc:
        logger.error(f"Task cleanup failed: {exc}")
        raise
