import logging

from celery import shared_task

from ..models import EmailMessage, Settings
from ..utils.summary import call_llm

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def llm_process_email(self, email_id, force=False):
    """
    Use LLM to organize, enrich, and summarize an email and its attachments.
    """
    try:
        email = EmailMessage.objects.select_related('user').get(id=email_id)
        user = email.user
    except EmailMessage.DoesNotExist:
        logger.error(f"EmailMessage id {email_id} does not exist")
        raise ValueError(f"EmailMessage id {email_id} does not exist")

    logger.info(f"LLM processing email: {email.subject}")

    # Set status to SUMMARY_PROCESSING at the start
    email.status = EmailMessage.ProcessingStatus.SUMMARY_PROCESSING
    email.save(update_fields=['status'])

    try:
        # Retrieve prompt_config from user settings
        try:
            prompt_setting = user.settings.get(
                key='prompt_config', is_active=True
            )
            prompt_config = prompt_setting.value
        except Settings.DoesNotExist:
            logger.error(f"User {user.username} has "
                         f"no active prompt_config setting")
            raise ValueError(
                f"User {user.username} has no active prompt_config setting")
        if not isinstance(prompt_config, dict):
            logger.error(f"User {user.username} prompt_config is not a dict")
            raise ValueError(
                f"User {user.username} prompt_config is not a dict")

        # Get all required prompts
        email_content_prompt = prompt_config.get('email_content_prompt')
        ocr_prompt = prompt_config.get('ocr_prompt')
        summary_prompt = prompt_config.get('summary_prompt')
        summary_title_prompt = prompt_config.get('summary_title_prompt')

        # Check required prompts
        if not email_content_prompt:
            logger.error(f"Missing email_content_prompt in prompt_config")
            raise ValueError("Missing email_content_prompt in prompt_config")
        if not ocr_prompt:
            logger.error(f"Missing ocr_prompt in prompt_config")
            raise ValueError("Missing ocr_prompt in prompt_config")
        if not summary_prompt or not summary_title_prompt:
            logger.error(f"Missing summary_prompt or summary_title_prompt "
                         f"in prompt_config")
            raise ValueError("Missing summary_prompt or "
                             "summary_title_prompt in prompt_config")

        # Step 1: Organize email body
        organize_email_body(email, email_content_prompt, force)

        # Step 2: Organize all image attachments' OCR content
        organize_attachments_ocr(email, ocr_prompt, force)

        # Step 3: Summarize title and content
        summarize_email(email, summary_prompt, summary_title_prompt, force)

        # Set status to SUMMARY_SUCCESS on success
        email.status = EmailMessage.ProcessingStatus.SUMMARY_SUCCESS
        email.save(update_fields=['status'])

        logger.info(f"LLM processed email: {email.subject}")
    except Exception as e:
        logger.error(f"Failed to process email {email.subject} with LLM: {e}")
        # Update email status to FAILED and record error message
        email.status = EmailMessage.ProcessingStatus.FAILED
        email.error_message = str(e)
        email.save(update_fields=['status', 'error_message'])
        raise

def organize_email_body(email, email_content_prompt, force=False):
    """
    Use LLM to organize/structure the email body/chat content.
    Save result to email.llm_content.
    """
    logger.info(f"Starting to organize email body: {email.subject}")
    if not force and email.llm_content:
        logger.info(f"Email {email.subject} already has LLM content, skipping")
        return

    # Prefer text_content > html_content > raw_content
    if email.text_content:
        content = email.text_content
    elif email.html_content:
        content = email.html_content
    else:
        content = email.raw_content

    # Call LLM (summary_chat)
    llm_result = call_llm(email_content_prompt, content)

    email.llm_content = llm_result.strip() if llm_result else ''
    email.save(update_fields=['llm_content'])

def organize_attachments_ocr(email, ocr_prompt, force=False):
    """
    Use LLM to organize/structure each image attachment's OCR content.
    Save result to attachment.llm_content.
    """
    logger.info(f"Starting to organize attachments OCR: {email.subject}")
    for att in email.attachments.filter(is_image=True):
        if not force and att.llm_content:
            logger.info(f"Attachment {att.id} already has "
                        f"LLM content, skipping")
            continue

        # Call LLM (summary_chat)
        llm_result = call_llm(ocr_prompt, att.ocr_content)

        att.llm_content = llm_result.strip() if llm_result else ''
        att.save(update_fields=['llm_content'])

def summarize_email(email, summary_prompt, summary_title_prompt, force=False):
    """
    Use LLM to generate summary_title and summary_content for the email.
    Include OCR processed content from attachments for comprehensive summary.
    """
    logger.info(f"Starting to summarize email: {email.subject}")
    if not force and email.summary_content and email.summary_title:
        logger.info(f"Email {email.subject} already has summary and "
                    f"title, skipping")
        return

    content = f"Subject: {email.subject}\nText Content: {email.llm_content}\n"

    # Collect all OCR processed content from attachments with filenames
    ocr_contents = []
    for att in email.attachments.filter(is_image=True):
        if att.llm_content:
            ocr_contents.append(
                f"[Attachment: {att.filename}]\n{att.llm_content}")

    # Combine email content with OCR contents
    combined_content = content
    if ocr_contents:
        combined_content += "\n\n--- ATTACHMENT OCR CONTENT ---\n\n"
        combined_content += "\n\n".join(ocr_contents)
        logger.info(f"Included {len(ocr_contents)} OCR contents in summary")

    summary_content = email.summary_content
    summary_title = email.summary_title

    if not summary_content or force:
        summary_content = call_llm(summary_prompt, combined_content)

    if not summary_title or force:
        summary_title = call_llm(summary_title_prompt, combined_content)

    email.summary_content = summary_content.strip() if summary_content else ''
    email.summary_title = summary_title.strip() if summary_title else ''
    email.save(update_fields=['summary_content', 'summary_title'])