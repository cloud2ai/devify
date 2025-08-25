import logging

from celery import shared_task
from django.utils import timezone
from django.utils.translation import activate, gettext_lazy as _

from devtoolbox.webhook import Webhook
from threadline.models import EmailMessage, Settings
from threadline.state_machine import EmailStatus

logger = logging.getLogger(__name__)

# Status to template color mapping for webhook notifications
STATUS_COLOR_MAPPING = {
    # Success states - Green
    'FETCHED': 'green',
    'OCR_SUCCESS': 'green',
    'SUMMARY_SUCCESS': 'green',
    'JIRA_SUCCESS': 'green',
    'SUCCESS': 'green',
    # Failed states - Red
    'OCR_FAILED': 'red',
    'SUMMARY_FAILED': 'red',
    'JIRA_FAILED': 'red',
    'FAILED': 'red',
    # Processing states - Blue
    'OCR_PROCESSING': 'blue',
    'SUMMARY_PROCESSING': 'blue',
    'JIRA_PROCESSING': 'blue',
    'ATTACHMENT_UPLOADING': 'blue',
    # Other states - Grey
    'PENDING': 'grey',
    'SKIPPED': 'grey',
    'ATTACHMENT_UPLOAD_FAILED': 'grey',
    'ATTACHMENT_UPLOADED': 'grey',
}

# Supported webhook providers
SUPPORTED_PROVIDERS = ['feishu']


def get_webhook_config(user):
    """
    Get webhook configuration from user's Settings key-value store.
    Returns empty dict if webhook is not properly configured.
    """
    try:
        webhook_setting = user.settings.get(
            key='webhook_config', is_active=True
        )
        webhook_config = webhook_setting.value
    except Settings.DoesNotExist:
        logger.debug(f"User {user.username} has no active webhook_config setting")
        return {}

    # Retrieve all webhook settings from user's webhook_config
    webhook_url = webhook_config.get('url', '').strip()
    webhook_events = webhook_config.get('events', [])
    webhook_timeout = webhook_config.get('timeout', 10)
    webhook_retries = webhook_config.get('retries', 3)
    webhook_headers = webhook_config.get('headers', {})
    webhook_language = webhook_config.get('language', 'zh-hans')
    provider = webhook_config.get('provider', 'feishu')

    # Check if webhook is properly configured
    if not webhook_url:
        logger.debug("Webhook URL is not configured")
        return {}

    # Return complete configuration if all checks pass
    return {
        'url': webhook_url,
        'events': webhook_events,
        'timeout': webhook_timeout,
        'retries': webhook_retries,
        'headers': webhook_headers,
        'language': webhook_language,
        'provider': provider
    }


def build_notification_payload(
    status, email, old_status=None, new_status=None, language=None
):
    """
    Build notification payload with generic message templates.
    Only payload fields are internationalized.
    """
    payload = {
        "status": status,
        "timestamp": timezone.now().isoformat(),
        "email_id": str(email.id),
        "subject": email.subject,
        "sender": email.sender,
        "user": email.user.username if email.user else None,
        "language": language or 'zh-hans',
    }
    # Add status transition information if available
    if old_status and new_status:
        payload.update({
            "old_status": old_status,
            "new_status": new_status,
            "status_transition": f"{old_status} -> {new_status}"
        })
    # Internationalized message content for webhook
    if status == EmailStatus.FETCHED.value:
        payload.update({
            "message": _(
                "New email received: {subject}"
            ).format(subject=email.subject),
            "stage": _("Email Fetching"),
            "details": _("From: {sender}").format(sender=email.sender)
        })
    elif status == EmailStatus.OCR_SUCCESS.value:
        payload.update({
            "message": _(
                "OCR processing completed: {subject}"
            ).format(subject=email.subject),
            "stage": _("OCR Processing"),
            "details": _("Image text extraction successful")
        })
    elif status == EmailStatus.OCR_FAILED.value:
        payload.update({
            "message": _(
                "OCR processing failed: {subject}"
            ).format(subject=email.subject),
            "stage": _("OCR Processing"),
            "details": _("Image text extraction failed")
        })
    elif status == EmailStatus.SUMMARY_SUCCESS.value:
        payload.update({
            "message": _(
                "LLM processing completed: {subject}"
            ).format(subject=email.subject),
            "stage": _("LLM Processing"),
            "details": _("Content analysis and summarization completed")
        })
    elif status == EmailStatus.SUMMARY_FAILED.value:
        payload.update({
            "message": _(
                "LLM processing failed: {subject}"
            ).format(subject=email.subject),
            "stage": _("LLM Processing"),
            "details": _("Content analysis failed")
        })
    elif status == EmailStatus.JIRA_SUCCESS.value:
        try:
            jira_issue = email.jiraissue_set.first()
            if jira_issue:
                payload.update({
                    "message": _(
                        "JIRA issue created successfully: {subject}"
                    ).format(subject=email.subject),
                    "stage": _("JIRA Creation"),
                    "jira_key": jira_issue.jira_issue_key,
                    "jira_url": jira_issue.jira_url,
                    "details": _(
                        "Issue: {key} | URL: {url}"
                    ).format(
                        key=jira_issue.jira_issue_key,
                        url=jira_issue.jira_url
                    )
                })
            else:
                payload.update({
                    "message": _(
                        "JIRA issue created successfully: {subject}"
                    ).format(subject=email.subject),
                    "stage": _("JIRA Creation"),
                    "details": _("Issue created but details not available")
                })
        except Exception:
            payload.update({
                "message": _(
                    "JIRA issue created successfully: {subject}"
                ).format(subject=email.subject),
                "stage": _("JIRA Creation"),
                "details": _("Issue created")
            })
    elif status == EmailStatus.JIRA_FAILED.value:
        payload.update({
            "message": _(
                "JIRA issue creation failed: {subject}"
            ).format(subject=email.subject),
            "stage": _("JIRA Creation"),
            "details": _("Failed to create JIRA issue")
        })
    else:
        # Fallback for generic status change
        payload.update({
            "message": _(
                "Status updated: {subject}"
            ).format(subject=email.subject),
            "stage": _("Processing"),
            "details": _(
                "Status changed from {old_status} to {new_status}"
            ).format(
                old_status=old_status,
                new_status=new_status
            )
        })
    return payload


def build_markdown_payload(status, email, old_status=None,
                         new_status=None, language=None):
    """
    Build Markdown card message parameters for Webhook
    """
    if language:
        activate(language)
    base_payload = build_notification_payload(
        status, email, old_status, new_status, language
    )
    template_color = STATUS_COLOR_MAPPING.get(status.upper(), "blue")
    timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
    title = _("[AI] Email Processing: {status}").format(status=status)
    details = base_payload.get('details', _('No details available'))
    markdown_content = (
        f"**{_('Time')}:** {timestamp}\n"
        f"**{_('Subject')}:** {email.subject}\n"
        f"**{_('Sender')}:** {email.sender}\n"
        f"**{_('Stage')}:** {base_payload.get('stage', _('Unknown'))}\n"
        f"**{_('Details')}:** {details}"
    )
    if 'jira_key' in base_payload:
        markdown_content += (
            f"\n**{_('JIRA Issue')}**: {base_payload['jira_key']}"
            f" ({base_payload['jira_url']})"
        )
    return {
        'title': title,
        'markdown_content': markdown_content,
        'template_color': template_color,
        'wide_screen_mode': True
    }

@shared_task(bind=True, max_retries=3)
def send_webhook_notification(self, email_id, old_status, new_status):
    """
    Send webhook notification with all business logic centralized here.
    Only webhook payload is internationalized. Logger messages are English only.
    """
    try:
        # Step 1.1: Get email object
        email = EmailMessage.objects.select_related('user').get(id=email_id)
        # Step 1.2: Get webhook configuration for this user
        config = get_webhook_config(email.user)
        if not config:
            logger.debug(
                f"Webhook not configured for user {email.user.username}, "
                f"skipping notification"
            )
            return
        # Step 1.5: Activate language for webhook payload
        language = config.get('language', 'zh-hans')
        activate(language)
        # Step 1.6: Validate provider
        provider = config.get('provider', 'feishu')
        if provider not in SUPPORTED_PROVIDERS:
            logger.error(
                f"Unsupported webhook provider: {provider}. "
                f"Supported providers: {SUPPORTED_PROVIDERS}"
            )
            return
        # Step 2: Check if new status matches any configured event
        configured_events = config.get('events', [])
        if not configured_events:
            logger.debug(
                "No events configured for notification"
            )
            return
        # Step 3: Check if the new status is in configured
        # events (case-insensitive)
        configured_events_lower = [
            event.lower() for event in configured_events]
        if new_status.lower() not in configured_events_lower:
            logger.debug(
                f"Skipping notification for status '{new_status}' "
                f"not in configured events: {configured_events}"
            )
            return
        # Step 4: Build notification payload and send
        markdown_params = build_markdown_payload(
            new_status, email, old_status, new_status, language=language
        )
        # Step 5: Send Markdown card message
        webhook = Webhook(config['url'])
        if provider == 'feishu':
            response = webhook.send_feishu_card_message(
                title=markdown_params['title'],
                markdown_content=markdown_params['markdown_content'],
                template_color=markdown_params['template_color'],
                wide_screen_mode=markdown_params['wide_screen_mode']
            )
        else:
            logger.error(
                f"Unsupported webhook provider: {provider}. "
                f"Supported providers: {SUPPORTED_PROVIDERS}"
            )
            return

        # Check response if available
        if response is not None and hasattr(response, 'status_code'):
            if response.status_code >= 400:
                raise Exception(
                    f"Webhook failed: {response.status_code}"
                )
        logger.info(
            f"Webhook notification sent successfully for status: {new_status}"
        )
    except Exception as exc:
        logger.error(
            f"Webhook notification failed: {exc}"
        )
        self.retry(countdown=60, exc=exc)
