import logging

from celery import shared_task
from django.utils import timezone
from django.utils.translation import activate, gettext_lazy as _

from devtoolbox.webhook import Webhook
from threadline.models import EmailMessage, Settings
from threadline.state_machine import EmailStatus

logger = logging.getLogger(__name__)

# Status color mapping for notifications
STATUS_COLORS = {
    'FETCHED': 'blue',
    'OCR_PROCESSING': 'blue',
    'OCR_SUCCESS': 'green',
    'OCR_FAILED': 'red',

    # LLM OCR processing status
    'LLM_OCR_PROCESSING': 'blue',
    'LLM_OCR_SUCCESS': 'green',
    'LLM_OCR_FAILED': 'red',

    # LLM Email processing (covers both body and attachments)
    'LLM_EMAIL_PROCESSING': 'blue',
    'LLM_EMAIL_SUCCESS': 'green',
    'LLM_EMAIL_FAILED': 'red',

    'LLM_SUMMARY_PROCESSING': 'blue',
    'LLM_SUMMARY_SUCCESS': 'green',
    'LLM_SUMMARY_FAILED': 'red',
    'ISSUE_PROCESSING': 'blue',
    'ISSUE_SUCCESS': 'green',
    'ISSUE_FAILED': 'red',
    'COMPLETED': 'green',
    # Add fallback colors for any other statuses
    'PENDING': 'grey',
    'RUNNING': 'blue',
    'SUCCESS': 'green',
    'FAILED': 'red',
    'SKIPPED': 'grey'
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
        logger.debug(f"User {user.username} has no active "
                     f"webhook_config setting")
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
    elif status == EmailStatus.LLM_OCR_PROCESSING.value:
        payload.update({
            "message": _(
                "LLM processing OCR results: {subject}"
            ).format(subject=email.subject),
            "stage": _("LLM OCR Processing"),
            "details": _("Processing OCR results with LLM")
        })
    elif status == EmailStatus.LLM_OCR_SUCCESS.value:
        payload.update({
            "message": _(
                "LLM OCR processing completed: {subject}"
            ).format(subject=email.subject),
            "stage": _("LLM OCR Processing"),
            "details": _("OCR results processed successfully")
        })
    elif status == EmailStatus.LLM_OCR_FAILED.value:
        payload.update({
            "message": _(
                "LLM OCR processing failed: {subject}"
            ).format(subject=email.subject),
            "stage": _("LLM OCR Processing"),
            "details": _("Failed to process OCR results with LLM")
        })
    elif status == EmailStatus.LLM_EMAIL_PROCESSING.value:
        payload.update({
            "message": _(
                "LLM processing email content: {subject}"
            ).format(subject=email.subject),
            "stage": _("LLM Email Processing"),
            "details": _("Processing email content with LLM")
        })
    elif status == EmailStatus.LLM_EMAIL_SUCCESS.value:
        payload.update({
            "message": _(
                "Email content has been organized and is ready for "
                "summary generation."
            ),
            "stage": _("Email Content Organization"),
            "details": _("Email content organized successfully")
        })
    elif status == EmailStatus.LLM_SUMMARY_SUCCESS.value:
        payload.update({
            "message": _(
                "Email summary has been generated successfully. "
                "Ready for issue creation."
            ),
            "stage": _("Summary Generation"),
            "details": _("Email summary generated successfully")
        })
    elif status == EmailStatus.LLM_EMAIL_FAILED.value:
        payload.update({
            "message": _(
                "Failed to organize email content. "
                "Please check the error details."
            ),
            "stage": _("Email Content Organization"),
            "details": _("Email content organization failed")
        })
    elif status == EmailStatus.LLM_SUMMARY_PROCESSING.value:
        payload.update({
            "message": _(
                "LLM generating summary: {subject}"
            ).format(subject=email.subject),
            "stage": _("LLM Summary Processing"),
            "details": _("Generating email summary with LLM")
        })
    elif status == EmailStatus.LLM_SUMMARY_FAILED.value:
        payload.update({
            "message": _(
                "Failed to generate email summary. "
                "Please check the error details."
            ),
            "stage": _("Summary Generation"),
            "details": _("Email summary generation failed")
        })
    elif status == EmailStatus.ISSUE_PROCESSING.value:
        payload.update({
            "message": _(
                "Creating issue: {subject}"
            ).format(subject=email.subject),
            "stage": _("Issue Creation"),
            "details": _("Creating JIRA issue")
        })
    elif status == EmailStatus.ISSUE_SUCCESS.value:
        try:
            jira_issue = email.jiraissue_set.first()
            if jira_issue:
                payload.update({
                    "message": _(
                        "Issue created successfully: {subject}"
                    ).format(subject=email.subject),
                    "stage": _("Issue Creation"),
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
                        "Issue created successfully: {subject}"
                    ).format(subject=email.subject),
                    "stage": _("Issue Creation"),
                    "details": _("Issue created but details not available")
                })
        except Exception:
            payload.update({
                "message": _(
                    "Issue created successfully: {subject}"
                ).format(subject=email.subject),
                "stage": _("Issue Creation"),
                "details": _("Issue created")
            })
    elif status == EmailStatus.ISSUE_FAILED.value:
        payload.update({
            "message": _(
                "Issue creation failed: {subject}"
            ).format(subject=email.subject),
            "stage": _("Issue Creation"),
            "details": _("Failed to create issue")
        })
    elif status == EmailStatus.COMPLETED.value:
        payload.update({
            "message": _(
                "Email processing completed: {subject}"
            ).format(subject=email.subject),
            "stage": _("Completed"),
            "details": _("All processing stages completed successfully")
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
    template_color = STATUS_COLORS.get(status.upper(), "blue")
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
