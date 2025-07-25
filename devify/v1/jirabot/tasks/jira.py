import logging
import re
import datetime

from celery import shared_task

from ..models import EmailMessage, JiraIssue, Settings
from ..utils.jira_handler import JiraHandler

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def submit_issue_to_jira(self, email_message_id):
    """
    Submit processed issue info to JIRA for a given email_message_id.
    """
    logger.info(
        f"Submitting JIRA issue for email_message_id={email_message_id}"
    )
    try:
        email = EmailMessage.objects.select_related('user').get(
            id=email_message_id
        )
    except EmailMessage.DoesNotExist:
        logger.error(
            f"EmailMessage id {email_message_id} does not exist"
        )
        return
    try:
        jira_setting = email.user.settings.get(
            key='jira_config', is_active=True
        )
        jira_config = jira_setting.value
    except Settings.DoesNotExist:
        logger.error(
            f"User {email.user} has no active jira_config setting"
        )
        return
    jira_url = jira_config.get('url')
    username = jira_config.get('username')
    password = jira_config.get('api_token')
    project_key = jira_config.get('project_key')
    issue_type = jira_config.get('default_issue_type', 'New Feature')
    priority = jira_config.get('default_priority', 'High')
    epic_link = jira_config.get('epic_link', '')
    assignee = jira_config.get('assignee', '')
    summary = email.summary_title or email.subject

    # Build JIRA summary with [AI] and today's date in [YYYYMMDD] format
    today_str = datetime.datetime.now().strftime('%Y%m%d')
    summary = f"[AI][{today_str}]{summary}"

    # Build comprehensive description with summary and LLM
    # content (with OCR inline)
    description_parts = []

    # Add summary content if available
    if email.summary_content:
        description_parts.append(email.summary_content)

    # Add LLM processed content if available
    llm_content = email.llm_content or ''
    attachments = list(email.attachments.filter(is_image=True))
    if llm_content:
        # Insert OCR content after each image reference in llm_content.
        # For every !filename! in llm_content, if there is a matching
        # attachment with OCR result, insert the OCR text right after the image.
        ocr_map = {
            att.filename: att.llm_content
            for att in attachments
            if att.llm_content
        }

        def replacer(match):
            """
            Replace image reference with OCR result if available.
            """
            fname = match.group(1)
            ocr_text = ocr_map.get(fname)
            if ocr_text:
                return (
                    f"!{match.group(1)}{match.group(2) or ''}!\n\n"
                    f"[OCR Result]{ocr_text}\n"
                )
            return match.group(0)

        # Insert OCR result after image reference in llm_content.
        # This regex supports both:
        #   !filename!                (e.g. !image.jpg!)
        #   !filename|width=600!      (e.g. !image.jpg|width=600!)
        # and any other parameters after '|'.
        llm_content_with_ocr = re.sub(
            r"!([\w@.\-]+)((?:\|[^!]*)?)!",
            replacer,
            llm_content
        )
        if description_parts:
            description_parts.append("--------------------------------")
        description_parts.append(llm_content_with_ocr)

    description = "\n\n".join(description_parts)
    try:
        handler = JiraHandler(jira_url, username, password)
        issue_key = handler.create_issue(
            project_key=project_key,
            summary=summary,
            issue_type=issue_type,
            description=description,
            priority=priority,
            epic_link=epic_link,
            assignee=assignee
        )
        logger.info(
            f"Successfully submitted JIRA issue {issue_key} "
            f"for email_message_id={email_message_id}"
        )
        # Upload attachments to JIRA issue
        attachments = email.attachments.all()
        logger.info(f"Found {attachments.count()} attachments to upload")
        for attachment in attachments:
            try:
                # Use original filename for JIRA upload to match email references
                original_filename = attachment.filename
                handler.upload_attachment(
                    issue_key=issue_key,
                    file_path=attachment.file_path,
                    filename=original_filename
                )
                logger.info(
                    f"Successfully uploaded attachment {original_filename} "
                    f"to issue {issue_key}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to upload attachment {original_filename} "
                    f"to issue {issue_key}: {e}"
                )
                continue
        # Create JiraIssue record after successful JIRA issue creation
        jira_issue_url = f"{jira_url}/browse/{issue_key}"
        JiraIssue.objects.create(
            user=email.user,
            email_message=email,
            jira_issue_key=issue_key,
            jira_url=jira_issue_url
        )
        email.status = EmailMessage.ProcessingStatus.JIRA_SUCCESS
        email.save(update_fields=['status'])
        return issue_key
    except Exception as e:
        logger.error(
            f"Failed to submit JIRA issue for "
            f"email_message_id={email_message_id}: {e}",
            exc_info=True
        )
        email.status = EmailMessage.ProcessingStatus.JIRA_FAILED
        email.save(update_fields=['status'])
        return