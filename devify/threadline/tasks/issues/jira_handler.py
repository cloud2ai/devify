"""
JIRA Issue Handler for external system integration.

This module handles JIRA-specific operations without any state management.
It's purely focused on JIRA API interactions.
"""

from datetime import datetime
import logging
import re
from typing import Dict, Any, Optional

from devtoolbox.api_clients.jira_client import JiraClient

from threadline.models import EmailMessage, Issue
from threadline.utils.summary import call_llm

logger = logging.getLogger(__name__)


class JiraIssueHandler:
    """
    Handler for JIRA operations, such as creating issues and
    uploading attachments.

    This class is purely focused on JIRA operations and doesn't
    handle any state management or workflow logic.
    """

    def __init__(self, jira_config: Dict[str, Any]):
        """
        Initialize JiraIssueHandler with JIRA configuration.

        Args:
            jira_config: JIRA configuration dictionary containing
                        url, username, api_token, etc.
        """
        self.jira_url = jira_config.get('url')
        self.username = jira_config.get('username')
        self.api_token = jira_config.get('api_token')
        self.project_key = jira_config.get('project_key')
        self.default_issue_type = jira_config.get(
            'default_issue_type', 'New Feature')
        self.default_priority = jira_config.get('default_priority', 'High')
        self.epic_link = jira_config.get('epic_link', '')
        self.assignee = jira_config.get('assignee', '')

        # LLM decision-making configuration
        self.allow_project_keys = jira_config.get('allow_project_keys', [])
        self.allow_assignees = jira_config.get('allow_assignees', [])
        self.project_prompt = jira_config.get('project_prompt', '')
        self.description_prompt = jira_config.get('description_prompt', '')
        self.assignee_prompt = jira_config.get('assignee_prompt', '')

        # Summary configuration
        self.summary_prefix = jira_config.get('summary_prefix', '[AI]')
        self.summary_timestamp = jira_config.get('summary_timestamp', False)

        # Create JiraClient for API operations
        self.client = JiraClient(
            jira_url=self.jira_url,
            username=self.username,
            password=self.api_token
        )

    def create_issue(
        self,
        issue: Issue,
        email: EmailMessage,
        force: bool = False
    ) -> str:
        """
        Create a JIRA issue from the given Issue object with LLM result caching.

        This method orchestrates the entire JIRA issue creation process:
        1. Builds summary with prefix and timestamp
        2. Processes description using LLM (with caching)
        3. Determines project key using LLM (with validation)
        4. Determines assignee using LLM (with validation)
        5. Creates the actual JIRA issue via API

        Args:
            issue: Issue object containing issue details
            email: EmailMessage object for additional context
            force: If True, force LLM processing even if cached results exist

        Returns:
            str: JIRA issue key (e.g., "PROJ-123")

        Raises:
            Exception: If JIRA issue creation fails
        """
        try:
            logger.info(f"Starting JIRA issue creation for email "
                        f"{email.id} (force={force})")

            # Step 1: Build issue summary with prefix and timestamp
            summary = self._build_jira_summary(email)
            # Store summary directly in Issue.title field
            issue.title = summary
            logger.debug(f"Built summary: {summary[:100]}...")

            # Step 2: Build comprehensive description using LLM if prompt
            # is available
            description_content = self._build_description(
                email,
                summary_only=False
            )
            logger.debug(f"Built description content: "
                         f"{len(description_content)} characters")

            # Process description with LLM and store directly in
            # Issue.description
            processed_description = self._process_with_llm(
                issue,
                self.description_prompt,
                description_content,
                'llm_description',
                default_value=description_content,
                force=force
            )

            """
            Clean the processed description for JIRA compatibility,
            remove emoji, and update the Issue object.
            """
            cleaned_description = self._remove_emoji(
                processed_description
            )[:10000]
            issue.description = cleaned_description
            logger.debug(
                f"Cleaned description: "
                f"{len(cleaned_description)} characters"
            )

            # Step 4: Determine project key using LLM if prompt is available
            summary_description = self._build_description(
                email,
                summary_only=True
            )
            final_project_key = self._process_with_llm(
                issue,
                self.project_prompt,
                summary_description,
                'llm_project_key',
                allowed_values=self.allow_project_keys,
                default_value=self.project_key,
                force=force
            )
            logger.info(f"Final project key: {final_project_key}")

            # Step 5: Determine assignee using LLM if prompt is available
            final_assignee = self._process_with_llm(
                issue,
                self.assignee_prompt,
                summary_description,
                'llm_assignee',
                allowed_values=self.allow_assignees,
                default_value=self.assignee,
                force=force
            )
            logger.info(f"Final assignee: {final_assignee}")

            # Step 6: Save Issue with updated title and description
            issue.save(update_fields=['title', 'description', 'metadata'])
            logger.debug(f"Updated Issue {issue.id} with title and description")

            # Step 7: Create JIRA issue via API
            logger.info(f"Creating JIRA issue with project={final_project_key}, "
                        f"assignee={final_assignee}")
            issue_key = self.client.create_issue(
                project_key=final_project_key,
                summary=summary,
                issue_type=self.default_issue_type,
                description=cleaned_description,
                assignee=final_assignee,
                priority=self.default_priority,
                epic_link=self.epic_link
            )

            logger.info(f"Successfully created JIRA issue: {issue_key} for email "
                        f"{email.id}")
            return issue_key

        except Exception as e:
            logger.error(f"Failed to create JIRA issue for email {email.id}: "
                         f"{e}", exc_info=True)
            raise

    def upload_attachments(
        self,
        issue_key: str,
        email: EmailMessage
    ) -> Dict[str, int]:
        """
        Upload email attachments to JIRA issue.

        Args:
            issue_key: JIRA issue key
            email: EmailMessage object containing attachments

        Returns:
            Dict: Upload results with counts
        """
        uploaded_count = 0
        skipped_count = 0

        # Upload image attachments with OCR content to JIRA.
        try:
            image_attachments = email.attachments.filter(is_image=True)
            for attachment in image_attachments:
                has_ocr = bool(attachment.ocr_content and
                               attachment.ocr_content.strip())
                if has_ocr:
                    try:
                        self.client.add_attachment(
                            issue=issue_key,
                            file_path=attachment.file_path
                        )
                        uploaded_count += 1
                        logger.debug(
                            f"Uploaded attachment {attachment.safe_filename} "
                            f"to {issue_key}"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to upload attachment "
                            f"{attachment.safe_filename}: {e}"
                        )
                        skipped_count += 1
                else:
                    skipped_count += 1
                    logger.debug(
                        f"Skipped attachment {attachment.safe_filename} "
                        f"(no OCR content)"
                    )
        except Exception as e:
            logger.error(
                f"Error uploading attachments to {issue_key}: {e}"
            )

        return {
            'uploaded_count': uploaded_count,
            'skipped_count': skipped_count
        }

    def _build_jira_summary(self, email: EmailMessage) -> str:
        """
        Build JIRA issue summary from email with prefix and timestamp.

        Summary building process:
        1. Extract base summary from email.summary_title or email.subject
        2. Apply configured prefix (e.g., '[AI]')
        3. Add timestamp if enabled (format: [YYYYMMDD])
        4. Clean for JIRA compatibility (remove line breaks, trim spaces)

        Args:
            email: EmailMessage object

        Returns:
            str: Clean summary for JIRA with prefix and timestamp
        """
        # Step 1: Extract base summary with fallback hierarchy
        summary = email.summary_title or email.subject or 'Email Issue'
        logger.debug(f"Base summary extracted: '{summary[:50]}...'")

        # Step 2: Build prefix with optional timestamp
        prefix = self.summary_prefix or ''
        logger.debug(f"Summary prefix configured: '{prefix}'")

        # Step 3: Add timestamp if configured
        if self.summary_timestamp:
            timestamp = datetime.now().strftime("%Y%m%d")
            prefix = f"{prefix}[{timestamp}]"
            logger.debug(f"Added timestamp to prefix: '{prefix}'")

        # Step 4: Combine prefix and summary
        final_summary = f"{prefix}{summary}"
        logger.debug(f"Final summary before cleaning: "
                     f"'{final_summary[:100]}...'")

        # Step 5: Clean for JIRA compatibility
        cleaned_summary = self._clean_jira_summary(final_summary)
        logger.info(f"Built JIRA summary: '{cleaned_summary}'")

        return cleaned_summary



    def _clean_jira_summary(self, summary: str) -> str:
        """
        Clean summary text for JIRA compatibility.

        Args:
            summary: Input summary text

        Returns:
            str: Cleaned summary text
        """
        if not summary:
            return ''
        # Remove line breaks and trim spaces
        return summary.replace('\n', ' ').replace('\r', ' ').strip()

    def _remove_emoji(self, text: str) -> str:
        """
        Remove emoji characters from text for JIRA compatibility.

        Args:
            text: Input text that may contain emoji characters

        Returns:
            str: Text with emoji characters removed
        """
        if not text:
            return ''

        # Remove emoji
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\u2600-\u26FF"          # miscellaneous symbols
            "\u2700-\u27BF"          # dingbats
            "\U0001F900-\U0001F9FF"  # supplemental symbols and pictographs
            "\U0001FA70-\U0001FAFF"  # symbols and pictographs extended-A
            "]+",
            flags=re.UNICODE
        )
        return emoji_pattern.sub('', text)

    def _process_embedded_images(self, llm_content: str, attachments) -> str:
        """
        Process embedded images in LLM content and add OCR LLM results.

        This method converts [IMAGE: filename] references in LLM content to:
        1. JIRA-compatible image format: !filename|width=600!
        2. OCR LLM processed content (if available)

        Process:
        1. Build mapping of filename -> OCR LLM content
        2. Find all [IMAGE: filename] references
        3. Replace with JIRA format + OCR LLM content

        Args:
            llm_content: The LLM processed content
            attachments: QuerySet of image attachments

        Returns:
            Processed content with JIRA image format and OCR LLM results
        """
        if not llm_content:
            logger.debug("No LLM content to process for embedded images")
            return ''

        logger.debug(f"Processing embedded images in {len(llm_content)} "
                     f"characters of LLM content")

        # Step 1: Create OCR LLM map for attachments with LLM processed content
        ocr_llm_map = {
            att.safe_filename or att.filename: att.llm_content
            for att in attachments
            if att.llm_content and att.llm_content.strip()
        }
        logger.debug(f"Found {len(ocr_llm_map)} attachments with OCR LLM content: "
                     f"{list(ocr_llm_map.keys())}")

        def replacer(match):
            """Replace [IMAGE: filename] with JIRA format and OCR LLM result."""
            fname = match.group(1)
            ocr_llm_text = ocr_llm_map.get(fname)

            # Convert to JIRA image format with default width
            jira_image = f"!{fname}|width=600!"

            if ocr_llm_text:
                logger.debug(f"Replaced [IMAGE: {fname}] with JIRA format + "
                             f"OCR LLM content")
                return f"{jira_image}\n\n{ocr_llm_text}\n"
            else:
                logger.debug(f"Replaced [IMAGE: {fname}] with JIRA format only "
                             f"(no OCR LLM content)")
                return jira_image

        # Step 2: Replace [IMAGE: filename] format with JIRA format and
        # OCR LLM content
        # This regex matches: [IMAGE: filename]
        processed_content = re.sub(
            r"\[IMAGE:\s*([\w@.\-]+)\]",
            replacer,
            llm_content
        )

        logger.info(f"Processed embedded images: "
                    f"{len(processed_content)} characters output")
        return processed_content

    def _get_embedded_filenames(self, llm_content: str) -> set:
        """
        Extract embedded image filenames from LLM content.

        Args:
            llm_content: The LLM processed content

        Returns:
            Set of embedded image filenames
        """
        if not llm_content:
            return set()

        # Extract from [IMAGE: filename] format
        embedded_matches = re.findall(
            r"\[IMAGE:\s*([\w@.\-]+)\]", llm_content
        )
        return set(embedded_matches)

    def _process_unembedded_images(
        self,
        attachments,
        embedded_filenames: set
    ) -> list:
        """
        Process images that are not embedded in the conversation.

        Args:
            attachments: QuerySet of image attachments
            embedded_filenames: Set of filenames already embedded in content

        Returns:
            List of formatted image content strings
        """
        unembedded_images = []

        for attachment in attachments:
            jira_filename = attachment.safe_filename or attachment.filename

            # Only process attachments that are not in embedded_filenames
            if (jira_filename not in embedded_filenames and
                attachment.llm_content and attachment.llm_content.strip()):

                image_content = []
                image_content.append(f"**Image: {jira_filename}**")

                # Embed the actual image using JIRA image syntax
                image_content.append(f"!{jira_filename}|width=600!")

                # Add LLM processed content (OCR + AI analysis)
                if attachment.llm_content:
                    image_content.append(
                        f"[OCR Result]\n{attachment.llm_content}"
                    )

                unembedded_images.append("\n".join(image_content))

        return unembedded_images

    def _build_description(
        self,
        email: EmailMessage,
        summary_only: bool = False
    ) -> str:
        """
        Build comprehensive description for JIRA issue.

        Description building process:
        1. Add email summary content (if available)
        2. Add separator line
        3. Add LLM content with embedded image processing
        4. Add separator line
        5. Add unembedded image content (images not referenced in LLM content)

        This creates a structured description with all relevant content
        from the email, including AI-processed images and summaries.

        Args:
            email: EmailMessage object
            summary_only: If True, only return summary content without
                         LLM content and unembedded images

        Returns:
            str: Formatted description ready for JIRA
        """
        logger.debug(f"Building description for email {email.id} "
                    f"(summary_only={summary_only})")
        content_parts = []

        # Step 1: Add summary content
        if email.summary_content and email.summary_content.strip():
            content_parts.append(email.summary_content.strip())
            logger.debug(f"Added summary content: "
                         f"{len(email.summary_content)} characters")
        else:
            logger.debug("No summary content available")

        # If summary_only is True, return only summary content
        if summary_only:
            combined = "\n".join(content_parts) if content_parts else ""
            logger.info(f"Built summary-only description: "
                       f"{len(combined)} characters total")
            return combined

        # Step 2: Add separator
        content_parts.append("\n---\n")

        # Step 3: Add LLM content with embedded image processing
        if email.llm_content and email.llm_content.strip():
            logger.debug(f"Processing LLM content: "
                         f"{len(email.llm_content)} characters")

            # Process embedded images in LLM content
            llm_content_with_images = self._process_embedded_images(
                email.llm_content,
                email.attachments.filter(is_image=True)
            )
            content_parts.append(llm_content_with_images)
            logger.debug(f"Added LLM content with images: "
                         f"{len(llm_content_with_images)} characters")
        else:
            logger.debug("No LLM content available")

        # Step 4: Add separator
        content_parts.append("\n---\n")

        # Step 5: Add unembedded image content
        embedded_filenames = self._get_embedded_filenames(
            email.llm_content or '')
        logger.debug(f"Found embedded filenames: {embedded_filenames}")

        unembedded_images = self._process_unembedded_images(
            email.attachments.filter(is_image=True), embedded_filenames
        )
        if unembedded_images:
            content_parts.append("\n\n".join(unembedded_images))
            logger.debug(f"Added {len(unembedded_images)} unembedded images")
        else:
            logger.debug("No unembedded images to add")

        # Step 6: Combine all parts
        combined = "\n".join(content_parts)
        logger.info(f"Built description: {len(combined)} characters total")

        return combined

    def _process_with_llm(
        self,
        issue: Issue,
        prompt: str,
        content: str,
        cache_key: str,
        allowed_values: Optional[list] = None,
        default_value: str = "",
        force: bool = False
    ) -> str:
        """
        Unified LLM processing method with caching and validation.

        This method provides a consistent interface for all LLM-based decisions:
        - Description formatting
          (stored in Issue.description field)
        - Project key selection
          (stored in issue.metadata, validated against
          allow_project_keys)
        - Assignee selection
          (stored in issue.metadata, validated against
          allow_assignees)

        Note: This method only caches results in metadata.
        The caller is responsible for updating the appropriate
        Issue fields (title, description) based on the processed
        results.

        Process flow:
        1. Check cache first (unless force mode)
        2. Initialize with default value
        3. Call LLM if prompt is configured
        4. Validate result against allowed_values (if provided)
        5. Cache and return final result

        Args:
            issue: Issue object for caching results
            prompt: LLM prompt text
            content: Content to process with LLM
            cache_key: Key for caching in issue.metadata
            allowed_values: List of allowed values (None = no validation)
            default_value: Default value if LLM fails or result is invalid
            force: If True, force LLM processing even if cached results exist

        Returns:
            str: Processed result
        """
        logger.debug(f"Processing {cache_key} with LLM (force={force})")

        # Step 1: Check cache first (unless force mode)
        if not force and cache_key in issue.metadata:
            cached_result = issue.metadata[cache_key]
            if cached_result:
                logger.info(f"Using cached {cache_key}: '{cached_result}'")
                return cached_result
            else:
                logger.debug(f"No valid cached result for {cache_key}")

        # Step 2: Initialize result with default value
        result = default_value
        logger.debug(f"Initialized {cache_key} with default: '{default_value}'")

        # Step 3: If prompt is configured, try LLM processing
        if prompt and prompt.strip():
            logger.info(f"Calling LLM for {cache_key} with "
                        f"{len(content)} characters of content")
            try:
                llm_result = call_llm(prompt, content)

                if not(llm_result and llm_result.strip()):
                    logger.warning(f"LLM returned empty result for {cache_key}")
                else:
                    llm_result = llm_result.strip()
                    logger.debug(f"LLM returned: '{llm_result}'")

                    # Step 4: Validate result if allowed_values provided
                    if allowed_values is None:
                        # No validation needed (e.g., for description)
                        result = llm_result
                        logger.info(f"LLM processing successful for {cache_key}: "
                                    f"'{result}'")
                    else:
                        # Validation required (e.g., for project_key, assignee)
                        if llm_result in allowed_values:
                            result = llm_result
                            logger.info(f"LLM selected valid {cache_key}: "
                                        f"'{result}'")
                        else:
                            logger.warning(
                                f"LLM returned invalid {cache_key} "
                                f"'{llm_result}', "
                                f"not in allowed list: {allowed_values}. "
                                f"Using default: '{default_value}'"
                            )

            except Exception as e:
                logger.error(f"Failed to process {cache_key} with LLM: {e}")
                logger.info(f"Using default value for {cache_key}: "
                            f"'{default_value}'")
        else:
            logger.info(f"No prompt configured for {cache_key}, using default: "
                        f"'{default_value}'")

        # Step 5: Cache the result
        issue.metadata[cache_key] = result
        issue.save(update_fields=['metadata'])
        logger.debug(f"Cached {cache_key}='{result}' for issue {issue.id}")

        return result
