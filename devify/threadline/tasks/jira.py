"""
JIRA Issue Creation Task using Celery Task class approach.

This module follows the same architecture pattern as ocr.py:
- Task class with before_start() for initialization
- run() method for main execution flow
- Helper methods for specific logic
- Compatibility wrapper function for existing calls

See ocr.py for detailed architecture documentation.
"""


# Import statements
from celery import Task, shared_task
import logging
import re
import datetime
from typing import Dict, Any

from ..models import EmailMessage, JiraIssue, Settings
from ..utils.jira_handler import JiraHandler
from ..state_machine import EmailStatus

logger = logging.getLogger(__name__)


class JiraTask(Task):
    """
    JIRA issue creation task using Celery Task class.

    This class provides a unified execution flow for JIRA issue creation
    while keeping all logic visible and maintainable.
    """

    def before_start(self, email_id: str, force: bool = False, **kwargs):
        """
        Initialize task before execution starts.

        This method handles all initialization work including:
        - Setting instance attributes
        - Getting email object

        Args:
            email_message_id: ID of the email to process
            force: Whether to force processing regardless of current status
            **kwargs: Additional arguments

        Raises:
            EmailMessage.DoesNotExist: If email not found
        """
        # Set instance attributes
        self.email_id = email_id
        self.force = force
        self.email = None
        self.task_name = "JIRA"
        self.allowed_statuses = [
            EmailStatus.SUMMARY_SUCCESS.value,
            EmailStatus.JIRA_FAILED.value
        ]

        # Get email object
        try:
            self.email = EmailMessage.objects.select_related('user').get(
                id=email_id
            )
            logger.info(f"[JIRA] Email object retrieved: {email_id}")
        except EmailMessage.DoesNotExist:
            logger.error(f"[JIRA] EmailMessage id {email_id} does not exist")
            raise

        logger.info(f"[JIRA] Initialization completed for {email_id}, "
                    f"force: {force}")

    def run(self, email_id: str, force: bool = False) -> str:
        """
        Main task execution method.

        Args:
            email_id: ID of the email to process
            force: Whether to force processing regardless of current status

        Returns:
            str: The email_id for the next task in the chain
        """
        try:
            # Initialize task
            #
            # Normal flow: Celery automatically calls before_start before run
            # Manual testing: Directly calling run method
            #   Check self.email doesn't exist → Call self.before_start to
            #   complete initialization
            #   Continue with business logic
            if not hasattr(self, 'email'):
                self.before_start(email_id, force)

            logger.info(f"[JIRA] Start processing: {email_id}, force: {force}")

            # Step 1: Pre-execution check (status machine + force parameter)
            if not self._pre_execution_check():
                logger.info(f"[JIRA] Pre-execution check failed, skipping to "
                            f"next task: {email_id}")
                return email_id

            # Step 2: Check if already complete
            if self._is_already_complete():
                return email_id

            # Step 3: Set processing status
            self._set_processing_status()

            # Step 4: Execute core business logic and complete task
            jira_results = self._execute_jira_creation()

            logger.info(f"[JIRA] JIRA issue creation task completed: {email_id}")
            return email_id

        except EmailMessage.DoesNotExist:
            logger.error(f"[JIRA] EmailMessage {email_id} not found")
            raise
        except Exception as exc:
            logger.error(f"[JIRA] Fatal error for {email_id}: {exc}")
            # Save error status to email (force mode handling is inside
            # _save_email)
            self._save_email(
                status=EmailStatus.JIRA_FAILED.value,
                error_message=str(exc)
            )
            raise

    def _pre_execution_check(self) -> bool:
        """
        Pre-execution check: Check if the task can be executed based on
        current status and force parameter.

        This is the main pre-execution check that combines:
        - Status machine validation
        - Force parameter handling

        Returns:
            bool: True if execution is allowed
        """
        if self.force:
            logger.debug(f"[JIRA] Force mode enabled for email "
                         f"{self.email.id}, skipping status check")
            return True

        if self.email.status not in self.allowed_statuses:
            logger.warning(
                f"Email {self.email.id} cannot be processed in status: "
                f"{self.email.status}. Allowed: {self.allowed_statuses}"
            )
            return False

        logger.debug(f"[JIRA] Pre-execution check passed for email "
                     f"{self.email.id}")
        return True

    def _is_already_complete(self) -> bool:
        """
        Check if JIRA issue creation is already complete.

        Returns:
            bool: True if already complete
        """
        if self.force:
            logger.debug(f"[JIRA] Force mode enabled for email "
                         f"{self.email.id}, skipping completion check")
            return False

        if (
            hasattr(self.email, 'jira_issues') and
            self.email.jira_issues.exists()
        ):
            logger.info(
                f"Email {self.email.id} already has JIRA issues, "
                f"skipping to next task"
            )
            return True

        return False

    def _set_processing_status(self) -> None:
        """
        Set the email to processing status.
        """
        self._save_email(status=EmailStatus.JIRA_PROCESSING.value)

    def _execute_jira_creation(self) -> Dict:
        """
        Execute JIRA issue creation for the email.

        Returns:
            Dict: JIRA creation results
        """
        try:
            jira_config = get_jira_config(self.email)
        except Settings.DoesNotExist:
            logger.error(
                f"User {self.email.user} has no active jira_config setting"
            )
            raise

        jira_url = jira_config.get('url')
        username = jira_config.get('username')
        password = jira_config.get('api_token')
        project_key = jira_config.get('project_key')
        issue_type = jira_config.get('default_issue_type', 'New Feature')
        priority = jira_config.get('default_priority', 'High')
        epic_link = jira_config.get('epic_link', '')
        assignee = jira_config.get('assignee', '')
        summary = build_jira_summary(self.email)

        # Build comprehensive description with summary and LLM
        # content (with OCR inline)
        description_parts = build_description_parts(self.email)

        description = "\n\n".join(description_parts)
        # Remove emoji from description
        description = remove_emoji(description)[:10000]

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
                f"for email_message_id={self.email.id}"
            )

            # Upload attachments to JIRA issue
            uploaded_count, skipped_count = upload_attachments_to_jira(
                handler, issue_key, self.email
            )

            # Create JiraIssue record after successful JIRA issue creation
            create_jira_issue_record(self.email, issue_key, jira_url)

            # Update email status to success (force mode handling is inside _save_email)
            self._save_email(status=EmailStatus.JIRA_SUCCESS.value)

            return {
                'issue_key': issue_key,
                'uploaded_count': uploaded_count,
                'skipped_count': skipped_count,
                'jira_url': jira_url
            }

        except Exception as e:
            logger.error(
                f"[JIRA] Failed to submit JIRA issue for "
                f"email_message_id={self.email.id}: {e}",
                exc_info=True
            )
            raise



    def _save_email(self, status: str = "", error_message: str = "") -> None:
        """
        Save email with status and error message.
        In force mode, skip status updates.

        Args:
            status: Status to set (only used in non-force mode)
            error_message: Error message to set (only used in non-force mode)
        """
        if self.force:
            # Force mode: skip status updates
            logger.debug(f"[JIRA] Force mode: skipping email status update to "
                         f"{status}")
            return

        # Non-force mode: save status
        self.email.status = status
        if error_message:
            self.email.error_message = error_message
        else:
            self.email.error_message = ""

        update_fields = ['status', 'error_message']
        self.email.save(update_fields=update_fields)
        logger.debug(f"[JIRA] Saved email {self.email.id} to {status}")


# Create JiraTask instance for Celery task registration
jira_task = JiraTask()


@shared_task(bind=True)
def submit_issue_to_jira(self, email_id: str, force: bool = False) -> str:
    """
    Celery task for submitting processed issue info to JIRA.

    This is a compatibility wrapper around the JiraTask class.

    Args:
        email_id (str): ID of the EmailMessage to process
        force (bool): Whether to force processing regardless of current status.
                     When True, skips status checks and allows reprocessing
                     even if the content already exists.

    Returns:
        str: The email_id for the next task in the chain
    """
    return jira_task.run(email_id, force)


# Helper functions (unchanged from original implementation)
def remove_emoji(text):
    """
    Remove emoji characters from text for JIRA compatibility.

    Args:
        text: Input text that may contain emoji characters

    Returns:
        Text with emoji characters removed
    """
    if not text:
        return ''
    # Remove emoji
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\u2600-\u26FF"
        "\u2700-\u27BF"
        "\U0001F900-\U0001F9FF"
        "\U0001FA70-\U0001FAFF"
        "]+",
        flags=re.UNICODE
    )
    return emoji_pattern.sub('', text)


def clean_jira_summary(summary):
    """
    Remove all line breaks and trim spaces for JIRA summary.

    Args:
        summary: Input summary text

    Returns:
        Cleaned summary text without line breaks
    """
    if summary is None:
        return ''
    return summary.replace('\n', ' ').replace('\r', ' ').strip()


def process_embedded_images(llm_content, attachments):
    """
    Process embedded images in LLM content and add OCR results.

    Args:
        llm_content: The LLM processed content
        attachments: List of image attachments

    Returns:
        Processed content with OCR results added after image references
    """
    if not llm_content:
        return ''

    # Create OCR map for attachments with both OCR and LLM content
    # Use UUID filename for mapping to match LLM content
    # LLM content uses [IMAGE: uuid.jpg] format as placeholders
    ocr_map = {
        att.safe_filename or att.filename: att.llm_content
        for att in attachments
        if att.ocr_content and att.ocr_content.strip() and att.llm_content
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

    # Insert OCR result after image reference in llm_content
    # This regex supports both:
    #   !filename!                (e.g. !image.jpg!)
    #   !filename|width=600!      (e.g. !image.jpg|width=600!)
    # and any other parameters after '|'.
    return re.sub(
        r"!([\w@.\-]+)((?:\|[^!]*)?)!",
        replacer,
        llm_content
    )


def get_embedded_filenames(llm_content):
    """
    Extract embedded image filenames from LLM content.

    Args:
        llm_content: The LLM processed content

    Returns:
        Set of embedded image filenames
    """
    if not llm_content:
        return set()

    embedded_matches = re.findall(
        r"!([\w@.\-]+)(?:\|[^!]*)?!", llm_content
    )
    return set(embedded_matches)


def process_unembedded_images(attachments, embedded_filenames):
    """
    Process images that are not embedded in the conversation.

    Args:
        attachments: List of image attachments
        embedded_filenames: Set of filenames already embedded in content

    Returns:
        List of formatted image content strings
    """
    unembedded_images = []
    unembedded_count = 0

    for attachment in attachments:
        # Use UUID filename for consistency with LLM content
        # LLM content uses [IMAGE: uuid.jpg] format as placeholders
        jira_filename = attachment.safe_filename or attachment.filename

        # NOTE(Ray): Current limitation - only processes attachments that are
        # not in embedded_filenames. This means if LLM content doesn't contain
        # image references, some attachments with OCR content may not be
        # included in JIRA description even though the actual files are
        # uploaded to JIRA. This is a known issue that needs to be addressed
        # in future iterations.
        if (jira_filename not in embedded_filenames and
            attachment.ocr_content and attachment.ocr_content.strip()):

            logger.info(
                f"Processing unembedded image: {jira_filename}"
            )
            image_content = []
            image_content.append(f"**Image: {jira_filename}**")

            # Embed the actual image using JIRA image syntax
            image_content.append(f"!{jira_filename}|width=600!")

            # Add OCR content
            if attachment.ocr_content:
                image_content.append(
                    f"[OCR Content]\n{attachment.ocr_content}"
                )

            # Add LLM summary if available
            if attachment.llm_content:
                image_content.append(
                    f"[AI Summary]\n{attachment.llm_content}"
                )

            unembedded_images.append("\n".join(image_content))
            unembedded_count += 1

    if unembedded_images:
        logger.info(
            f"Adding {unembedded_count} unembedded images to description"
        )

    return unembedded_images


def build_description_parts(email):
    """
    Build description parts for JIRA issue.

    Args:
        email: EmailMessage object

    Returns:
        List of description parts to be joined
    """
    description_parts = []

    # Add summary content if available
    if email.summary_content:
        description_parts.append(email.summary_content)

    # Add LLM processed content if available
    llm_content = email.llm_content or ''
    attachments = list(email.attachments.filter(is_image=True))

    if llm_content:
        # Process embedded images and add OCR results
        llm_content_with_ocr = process_embedded_images(
            llm_content, attachments
        )
        if description_parts:
            description_parts.append("--------------------------------")
        description_parts.append(llm_content_with_ocr)

    # Add unembedded image content with OCR results and summaries
    embedded_filenames = get_embedded_filenames(llm_content)
    if llm_content:
        logger.info(
            f"Found {len(embedded_filenames)} embedded images in LLM content"
        )

    # NOTE(Ray): Current implementation limitation
    # The system only includes OCR content for images that are explicitly
    # referenced in the LLM content. Images that exist as attachments but
    # are not mentioned in the conversation text may have their OCR content
    # excluded from the JIRA description, even though the actual image files
    # are uploaded to JIRA.
    #
    # This means:
    # - Images referenced in LLM content: OCR content included in description
    # - Images not referenced in LLM content: Only file uploaded, no OCR
    #   content in description
    #
    # TODO(Ray): Future improvement needed to ensure all image OCR content
    # is included regardless of whether they are referenced in the conversation
    # text.
    unembedded_images = process_unembedded_images(
        attachments, embedded_filenames
    )

    # Append unembedded image content to description
    if unembedded_images:
        if description_parts:
            description_parts.append("--------------------------------")
        description_parts.append("**Additional Images:**")
        description_parts.extend(unembedded_images)

    return description_parts


def upload_attachments_to_jira(handler, issue_key, email):
    """
    Upload attachments to JIRA issue with proper filtering and error handling.

    Args:
        handler: JiraHandler instance
        issue_key: JIRA issue key
        email: EmailMessage object

    Returns:
        Tuple of (uploaded_count, skipped_count)
    """
    attachments = email.attachments.all()
    logger.info(f"Found {attachments.count()} total attachments")

    uploaded_count = 0
    skipped_count = 0

    for attachment in attachments:
        # Skip image attachments with empty OCR content
        if (attachment.is_image and
            (not attachment.ocr_content or not attachment.ocr_content.strip())):
            logger.info(
                f"Skipping image attachment {attachment.filename} "
                f"- no OCR content available"
            )
            skipped_count += 1
            continue

        try:
            # Use UUID filename for JIRA upload to match text placeholders
            # LLM content uses [IMAGE: uuid.jpg] format as placeholders
            jira_filename = attachment.safe_filename or attachment.filename
            handler.upload_attachment(
                issue_key=issue_key,
                file_path=attachment.file_path,
                filename=jira_filename
            )
            logger.info(
                f"Successfully uploaded attachment {jira_filename} "
                f"to issue {issue_key}"
            )
            uploaded_count += 1
        except Exception as e:
            logger.error(
                f"Failed to upload attachment {jira_filename} "
                f"to issue {issue_key}: {e}"
            )
            continue

    # NOTE(Ray): Attachment upload vs OCR content inclusion
    # This function handles file upload to JIRA, but OCR content inclusion
    # in the JIRA description is handled separately in
    # build_description_parts().
    #
    # Current behavior:
    # - Files are uploaded to JIRA (this function)
    # - OCR content is only included if the image is referenced in LLM content
    # - This can lead to situations where files exist in JIRA but their
    #   OCR content is missing from the description
    logger.info(
        f"Attachment upload completed: {uploaded_count} uploaded, "
        f"{skipped_count} skipped (no OCR content)"
    )
    return uploaded_count, skipped_count


def create_jira_issue_record(email, issue_key, jira_url):
    """
    Create JiraIssue record in database after successful JIRA issue creation.

    Args:
        email: EmailMessage object
        issue_key: JIRA issue key
        jira_url: JIRA base URL

    Returns:
        Created JiraIssue object
    """
    jira_issue_url = f"{jira_url}/browse/{issue_key}"
    jira_issue = JiraIssue.objects.create(
        user=email.user,
        email_message=email,
        jira_issue_key=issue_key,
        jira_url=jira_issue_url
    )
    return jira_issue


def get_jira_config(email):
    """
    Get JIRA configuration from user settings.

    Args:
        email: EmailMessage object

    Returns:
        JIRA configuration dictionary

    Raises:
        Settings.DoesNotExist: If user has no active jira_config setting
    """
    jira_setting = email.user.settings.get(
        key='jira_config', is_active=True
    )
    return jira_setting.value


def build_jira_summary(email):
    """
    Build JIRA summary with AI prefix and date.

    Args:
        email: EmailMessage object

    Returns:
        Formatted summary string
    """
    summary = email.summary_title or email.subject

    # Build JIRA summary with [AI] and today's date in [YYYYMMDD] format
    today_str = datetime.datetime.now().strftime('%Y%m%d')
    summary = f"[AI][{today_str}]{summary}"

    # Remove line breaks and emoji from summary
    summary = clean_jira_summary(summary)
    summary = remove_emoji(summary)[:500]

    return summary
