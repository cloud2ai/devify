import logging
from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from threadline.tasks.email_fetch import scan_user_emails
from threadline.models import EmailMessage
from threadline.state_machine import EmailStatus
from threadline.tasks.chain_orchestrator import process_email_chain
from threadline.utils.email_processor import EmailProcessor, EmailSource

logger = logging.getLogger(__name__)

# Configuration for stuck email handling
# Each item defines: (reset_to_status, description)
STUCK_STATUS_RESET_MAP = {
    # Processing states that might get stuck
    EmailStatus.OCR_PROCESSING.value: (
        EmailStatus.FETCHED.value,
        'OCR'
    ),
    EmailStatus.LLM_EMAIL_PROCESSING.value: (
        EmailStatus.FETCHED.value,
        'LLM_EMAIL'
    ),
    EmailStatus.LLM_SUMMARY_PROCESSING.value: (
        EmailStatus.FETCHED.value,
        'LLM_SUMMARY'
    ),
    EmailStatus.ISSUE_PROCESSING.value: (
        EmailStatus.FETCHED.value,
        'Issue'
    ),

    # Success states that might get stuck in chain
    # Reset all to FETCHED to restart the entire processing chain
    EmailStatus.OCR_SUCCESS.value: (
        EmailStatus.FETCHED.value,
        'OCR_SUCCESS'
    ),
    EmailStatus.LLM_EMAIL_SUCCESS.value: (
        EmailStatus.FETCHED.value,
        'LLM_EMAIL_SUCCESS'
    ),
    EmailStatus.LLM_SUMMARY_SUCCESS.value: (
        EmailStatus.FETCHED.value,
        'LLM_SUMMARY_SUCCESS'
    ),
    EmailStatus.ISSUE_SUCCESS.value: (
        EmailStatus.FETCHED.value,
        'ISSUE_SUCCESS'
    ),
}


@shared_task
def schedule_email_processing_tasks():
    """
    Unified scheduler for driving email processing tasks based on status.

    This scheduler now uses the new chain-based approach for better
    workflow management and error handling.
    """
    # Schedule complete processing chain for emails that are ready to start
    for email in EmailMessage.objects.filter(
        status=EmailStatus.FETCHED.value
    ):
        logger.info(
            f"Scheduling complete processing chain for email id={email.id}, "
            f"subject={email.subject}"
        )
        process_email_chain.delay(email.id)


@shared_task
def schedule_reset_stuck_processing_emails(timeout_minutes=30):
    """
    Scan and reset emails stuck in any state for over timeout_minutes.

    This task identifies emails that have been stuck in any processing
    or success state for longer than the specified timeout and resets
    them to FETCHED state to restart the entire processing chain.

    Args:
        timeout_minutes (int): Minutes after which emails are considered stuck
    """
    now = timezone.now()

    # Get all stuck emails in one query using 'in' operator
    stuck_statuses = list(STUCK_STATUS_RESET_MAP.keys())
    stuck_emails = EmailMessage.objects.filter(
        status__in=stuck_statuses,
        updated_at__lt=now - timedelta(minutes=timeout_minutes)
    )

    # Process each stuck email
    reset_results = {}
    for email in stuck_emails:
        reset_to_status, description = STUCK_STATUS_RESET_MAP[email.status]

        logger.warning(
            f"Email {email.id} stuck in {email.status} for "
            f"{timeout_minutes}+ minutes, resetting to {reset_to_status}"
        )

        # Save the old status for logging
        old_status = email.status

        # Update the email status and persist the change
        email.status = reset_to_status
        email.save(update_fields=['status'])

        # Log the status reset with controlled line length
        logger.info(
            "[Scheduler] Reset email %s from %s to %s",
            email.id,
            old_status,
            reset_to_status
        )

        # Count resets by description
        reset_results[description] = reset_results.get(description, 0) + 1

    # Log summary if any emails were reset
    total_reset = sum(reset_results.values())

    if total_reset > 0:
        logger.info(
            "Reset %d stuck emails: %s",
            total_reset,
            ", ".join(
                [
                    f"{count} {desc}"
                    for desc, count in reset_results.items()
                    if count > 0
                ]
            ),
        )


@shared_task
def schedule_user_email_scanning():
    """
    Schedule email scanning for all active users.

    This task iterates through all users and schedules individual
    email scanning tasks for each user.
    """

    User = get_user_model()

    # Get all active users
    active_users = User.objects.filter(is_active=True)

    logger.info(f"Scheduling email scanning for {active_users.count()} "
                f"active users")

    # Schedule email scanning for each user
    for user in active_users:
        try:
            # Check if user has email configuration
            from threadline.models import Settings
            email_config = Settings.objects.filter(
                user=user,
                key='email_config',
                is_active=True
            ).first()

            if email_config:
                logger.info(f"Scheduling email scan for user: {user.username}")
                scan_user_emails.delay(user.id)
            else:
                logger.debug(f"User {user.username} has no email "
                             "configuration, skipping")

        except Exception as e:
            logger.error(f"Failed to schedule email scan for user "
                         f"{user.username}: {e}")

    logger.info("User email scanning scheduling completed")


@shared_task(bind=True, max_retries=3)
def process_file_emails_task(self):
    """
    Celery task to process file-based emails from Haraka
    Processes emails from inbox directory and moves them to appropriate folders
    """
    try:
        processor = EmailProcessor(
            source=EmailSource.FILE,
            parser_type='flanker'  # Use EmailFlankerParser
        )

        # Process emails using the unified processor
        processed_count = 0
        for parsed_email in processor.process_emails():
            processed_count += 1

        logger.info(f'File email processing completed: {processed_count} '
                    f'emails processed')

        return {
            'processed': processed_count,
            'status': 'success'
        }

    except Exception as exc:
        logger.error(f'File email processing task failed: {exc}')

        # Retry the task with exponential backoff
        raise self.retry(
            exc=exc,
            countdown=60 * (2 ** self.request.retries),
            max_retries=3
        )
