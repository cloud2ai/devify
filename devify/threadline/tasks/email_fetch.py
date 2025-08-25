import logging
import os
import shutil
from datetime import datetime, timedelta
from django.utils import timezone

from celery import shared_task
from django.contrib.auth.models import User

from threadline.models import EmailAttachment, EmailMessage, EmailTask, Settings
from threadline.utils.email_client import EmailClient
from django.conf import settings
from threadline.state_machine import EmailStatus

logger = logging.getLogger(__name__)

DEFAULT_EMAIL_FETCH_DAYS = 7


def get_user_email_settings(user_id):
    """
    Get user email settings directly from Settings table.
    Returns tuple of (email_config, email_filter_config) or (None, None).
    """
    user_settings = Settings.objects.filter(
        user_id=user_id,
        key__in=['email_config', 'email_filter_config'],
        is_active=True
    ).values('key', 'value')

    email_config = None
    email_filter_config = None

    for setting in user_settings:
        if setting['key'] == 'email_config':
            email_config = setting['value']
        elif setting['key'] == 'email_filter_config':
            email_filter_config = setting['value']

    # Provide default email_filter_config if not found
    if not email_filter_config:
        email_filter_config = {
            'folder': 'INBOX',
            'filters': [],
            'exclude_patterns': [
                'spam',
                'newsletter'
            ],
            'max_age_days': DEFAULT_EMAIL_FETCH_DAYS
        }

    # If 'last_email_fetch_time' exists in email_filter_config, use it as the
    # starting point for fetching emails; otherwise, default to 7 days ago.
    if email_filter_config:
        last_fetch_time = email_filter_config.get('last_email_fetch_time')
        if last_fetch_time:
            # Parse ISO format datetime with timezone
            since_dt = datetime.fromisoformat(last_fetch_time)
            # Convert to timezone-aware datetime if naive
            if timezone.is_naive(since_dt):
                since_dt = timezone.make_aware(since_dt)
            # Convert to local timezone for IMAP search
            since_dt = timezone.localtime(since_dt)
        else:
            since_dt = timezone.now() - timedelta(
                days=DEFAULT_EMAIL_FETCH_DAYS)
        email_filter_config['since'] = since_dt.strftime('%d-%b-%Y')
    logger.info(f"Filter email config: {email_filter_config}")

    return email_config, email_filter_config


def _save_email_attachments(user, email_msg, attachments):
    """
    Move attachments to target dir and create EmailAttachment records.
    Use the basename of att['file_path'] as the filename to avoid conflicts.
    """
    message_id = email_msg.message_id
    attachment_dir = os.path.join(
        settings.EMAIL_ATTACHMENT_STORAGE_PATH,
        message_id
    )
    os.makedirs(attachment_dir, exist_ok=True)
    logger.info(f"Created attachment directory: {attachment_dir}")

    created_attachments = []
    for att in attachments:
        logger.info(f"Attachment meta: {att}")
        old_path = att.get('file_path', '')
        # Use the processed unique filename
        filename = os.path.basename(old_path)
        if old_path and os.path.exists(old_path):
            new_path = os.path.join(attachment_dir, filename)
            try:
                shutil.move(old_path, new_path)
                logger.info(f"Moved attachment {filename} to {new_path}")
                att['file_path'] = new_path
            except Exception as move_err:
                logger.error(f"Failed to move attachment "
                             f"{filename}: {move_err}")
                new_path = old_path
        else:
            logger.warning(f"Attachment file not found: {old_path}")
            new_path = old_path

        email_att = EmailAttachment.objects.create(
            user=user,
            email_message=email_msg,
            filename=att.get('filename', 'unknown'),
            safe_filename=att.get('safe_filename', ''),
            content_type=att.get('content_type', ''),
            file_size=att.get('file_size', 0),
            file_path=new_path,
            is_image=att.get('is_image', False),
        )

        logger.info(f"EmailAttachment created: {email_att}")
        created_attachments.append(email_att)
    return created_attachments


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
        logger.info(f"Starting email fetch for user {user.username}")

        email_config, email_filter_config = get_user_email_settings(user_id)
        if not email_config:
            logger.warning(
                f"Skipping email fetch for user {user.username} "
                f"due to missing email_config"
            )
            return

        client = EmailClient(
            email_config,
            email_filter_config,
            settings.TMP_EMAIL_ATTACHMENT_STORAGE_PATH
        )

        # Set email task to running
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
                email_msg = EmailMessage.objects.create(
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
                    status=EmailStatus.FETCHED.value,
                )
                attachments = mail.get('attachments', [])
                logger.info(f"mail['attachments'] = {attachments}")
                logger.info(f"Number of attachments: {len(attachments)}")

                _save_email_attachments(user, email_msg, attachments)
                new_emails.append(mail)
            else:
                logger.warning(f"Skipping email with "
                               f"subject: {mail['subject']}")

        # Update last_email_fetch_time if new emails fetched
        if new_emails:
            max_received = max(mail['received_at'] for mail in new_emails)
            # Set the last email fetch time in ISO format
            email_filter_config[
                'last_email_fetch_time'
            ] = max_received.isoformat()

            # Update settings directly
            Settings.objects.filter(
                user_id=user_id,
                key='email_filter_config',
                is_active=True
            ).update(value=email_filter_config)

        email_task.status = EmailTask.TaskStatus.COMPLETED
        email_task.emails_processed = len(new_emails)
        email_task.save(update_fields=['status', 'emails_processed'])
        logger.info(f"Fetched {len(new_emails)} new emails "
                    f"for user {user.username}")

    except Exception as e:
        logger.error(f"Failed to fetch emails for user {user_id}: {e}")
        if email_task:
            email_task.status = EmailTask.TaskStatus.FAILED
            email_task.error_message = str(e)
            email_task.save(update_fields=['status', 'error_message'])
