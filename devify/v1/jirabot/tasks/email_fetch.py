import logging
from datetime import datetime, timedelta

from celery import shared_task
from django.contrib.auth.models import User

from v1.jirabot.models import EmailMessage, EmailTask, Settings
from v1.jirabot.utils.email_client import EmailClient
from core.settings.globals import EMAIL_ATTACHMENT_STORAGE_PATH

logger = logging.getLogger(__name__)

DEFAULT_EMAIL_FETCH_DAYS = 7


def get_user_email_settings(user_id):
    """
    Get user email settings directly from Settings table.
    Returns tuple of (email_config, email_filter_config) or (None, None).
    """
    settings = Settings.objects.filter(
        user_id=user_id,
        key__in=['email_config', 'email_filter_config'],
        is_active=True
    ).values('key', 'value')

    email_config = None
    email_filter_config = None

    for setting in settings:
        if setting['key'] == 'email_config':
            email_config = setting['value']
        elif setting['key'] == 'email_filter_config':
            email_filter_config = setting['value']

    # Provide default email_filter_config if not found
    if not email_filter_config:
        email_filter_config = {
            'folder': 'INBOX',
            'since': (datetime.now() - timedelta(days=7)).strftime('%d-%b-%Y')
        }

    # If 'last_email_fetch_time' exists in email_filter_config, use it as the
    # starting point for fetching emails; otherwise, default to 7 days ago.
    if email_filter_config:
        last_fetch_time = email_filter_config.get('last_email_fetch_time')
        if last_fetch_time:
            since_dt = datetime.fromisoformat(last_fetch_time)
        else:
            since_dt = datetime.now() - timedelta(
                days=DEFAULT_EMAIL_FETCH_DAYS)
        email_filter_config['since'] = since_dt.strftime('%d-%b-%Y')

    return email_config, email_filter_config


@shared_task(bind=True)
def scan_user_emails(self, user_id):
    """
    Fetch new emails for a specific user and save as EmailMessage.
    Use last_email_fetch_time in email_filter_config for incremental fetch.
    """
    email_task = None
    try:
        # Get user and settings in one query
        user = User.objects.get(id=user_id)
        email_config, email_filter_config = get_user_email_settings(user_id)

        if not email_config:
            logger.warning(
                f"Missing email_config for user {user.username}"
            )
            return

        client = EmailClient(
            email_config,
            email_filter_config,
            EMAIL_ATTACHMENT_STORAGE_PATH
        )

        email_task = EmailTask.objects.create(
            user=user,
            status=EmailTask.TaskStatus.RUNNING
        )

        new_emails = []
        for mail in client.scan_emails():
            message_id = mail['message_id']
            if not EmailMessage.objects.filter(
                user=user, message_id=message_id).exists():
                logger.info(f"Found new email with message_id: {message_id}")
                EmailMessage.objects.create(
                    user=user,
                    task=email_task,
                    subject=mail['subject'],
                    sender=mail['sender'],
                    recipients=mail['recipients'],
                    received_at=mail['received_at'],
                    raw_content=mail['raw_content'],
                    html_content=mail['html_content'],
                    text_content=mail['text_content'],
                    message_id=message_id,
                    status=EmailMessage.ProcessingStatus.FETCHED,
                )
                new_emails.append(mail)

        # Update last_email_fetch_time if new emails fetched
        if new_emails:
            max_received = max(mail['received_at'] for mail in new_emails)
            email_filter_config['last_email_fetch_time'] = max_received.isoformat()

            # Update settings directly
            Settings.objects.filter(
                user_id=user_id,
                key='email_filter_config',
                is_active=True
            ).update(value=email_filter_config)

        email_task.status = EmailTask.TaskStatus.COMPLETED
        email_task.emails_processed = len(new_emails)
        email_task.save(update_fields=['status', 'emails_processed'])
        logger.info(f"Fetched {len(new_emails)} new emails for user {user.username}")

    except Exception as e:
        logger.error(f"Failed to fetch emails for user {user_id}: {e}")
        if email_task:
            email_task.status = EmailTask.TaskStatus.FAILED
            email_task.error_message = str(e)
            email_task.save(update_fields=['status', 'error_message'])

@shared_task
def scan_all_users_emails():
    """
    Periodically fetch emails for all users with active email_config.
    """
    users = User.objects.filter(
        settings__key='email_config',
        settings__is_active=True
    ).distinct()
    for user in users:
        scan_user_emails.delay(user.id)
    logger.info(f"Scheduled scan_user_emails for {users.count()} users")