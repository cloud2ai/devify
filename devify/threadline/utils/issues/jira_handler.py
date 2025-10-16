"""
JIRA Issue Handler for external system integration.

This module handles JIRA-specific operations without any state management.
It's purely focused on JIRA API interactions.

Design principle: This handler should NOT use Django ORM models.
All data should be passed as dictionaries to avoid database dependencies.
"""

from datetime import datetime
import logging
import os
import re
from typing import Dict, Any, Optional, List

from devtoolbox.api_clients.jira_client import JiraClient

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
        issue_data: Dict[str, Any],
        email_data: Dict[str, Any],
        attachments: List[Dict[str, Any]],
        force: bool = False
    ) -> str:
        """
        Create a JIRA issue from pure data dictionaries (no ORM objects).

        This method orchestrates the entire JIRA issue creation process:
        1. Builds summary with prefix and timestamp
        2. Processes description using LLM
        3. Determines project key using LLM (with validation)
        4. Determines assignee using LLM (with validation)
        5. Creates the actual JIRA issue via API

        Args:
            issue_data: Dict containing issue information
                - title: Issue title/summary
                - description: Issue description
                - priority: Issue priority
            email_data: Dict containing email information
                - id: Email ID
                - summary_title: Email summary title
                - summary_content: Email summary content
                - llm_content: LLM processed content
                - subject: Email subject
            attachments: List of attachment dicts
                - filename: Attachment filename
                - safe_filename: Safe filename for JIRA
                - content_type: Content type
                - is_image: Whether it's an image
                - ocr_content: OCR content (for images)
                - llm_content: LLM processed content
                - file_path: Path to attachment file
            force: If True, force LLM processing

        Returns:
            str: JIRA issue key (e.g., "PROJ-123")

        Raises:
            Exception: If JIRA issue creation fails
        """
        try:
            email_id = email_data.get('id')
            logger.info(
                f"Starting JIRA issue creation for email {email_id} "
                f"(force={force})"
            )

            summary = self._build_jira_summary(email_data)
            logger.debug(f"Built summary: {summary[:100]}...")

            description_content = self._build_description(
                email_data,
                attachments,
                summary_only=False
            )
            logger.debug(
                f"Built description content: "
                f"{len(description_content)} characters"
            )

            processed_description = self._process_description_with_llm(
                description_content,
                force=force
            )

            cleaned_description = self._remove_emoji(
                processed_description
            )[:10000]
            logger.debug(
                f"Cleaned description: {len(cleaned_description)} characters"
            )

            summary_description = self._build_description(
                email_data,
                attachments,
                summary_only=True
            )

            final_project_key = self._determine_project_key(
                summary_description,
                force=force
            )
            logger.info(f"Final project key: {final_project_key}")

            final_assignee = self._determine_assignee(
                summary_description,
                force=force
            )
            logger.info(f"Final assignee: {final_assignee}")

            logger.info(
                f"Creating JIRA issue with project={final_project_key}, "
                f"assignee={final_assignee}"
            )
            issue_key = self.client.create_issue(
                project_key=final_project_key,
                summary=summary,
                issue_type=self.default_issue_type,
                description=cleaned_description,
                assignee=final_assignee,
                priority=self.default_priority,
                epic_link=self.epic_link
            )

            logger.info(
                f"Successfully created JIRA issue: {issue_key} "
                f"for email {email_id}"
            )
            return issue_key

        except Exception as e:
            logger.error(
                f"Failed to create JIRA issue for email "
                f"{email_data.get('id')}: {e}",
                exc_info=True
            )
            raise

    def upload_attachments(
        self,
        issue_key: str,
        attachments: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        Upload attachments to JIRA issue from pure data (no ORM objects).

        Args:
            issue_key: JIRA issue key
            attachments: List of attachment dicts
                - filename: Attachment filename
                - content_type: Content type
                - is_image: Whether it's an image
                - ocr_content: OCR content (for images)
                - file_path: Path to attachment file
                - file_size: File size in bytes

        Returns:
            Dict: Upload results with counts
                - uploaded_count: Number of uploaded files
                - skipped_count: Number of skipped files
        """
        uploaded_count = 0
        skipped_count = 0

        try:
            logger.info(
                f"Found {len(attachments)} total attachments "
                f"for issue {issue_key}"
            )

            for attachment in attachments:
                filename = attachment.get('filename', 'unknown')
                content_type = attachment.get('content_type', '')
                is_image = attachment.get('is_image', False)
                file_path = attachment.get('file_path', '')
                file_size = attachment.get('file_size', 0)

                logger.info(
                    f"Processing attachment: {filename} "
                    f"(type: {content_type}, is_image: {is_image}, "
                    f"size: {file_size} bytes)"
                )

                if not os.path.exists(file_path):
                    logger.warning(f"Attachment file not found: {file_path}")
                    skipped_count += 1
                    continue

                should_upload = True
                skip_reason = ""

                if is_image:
                    ocr_content = attachment.get('ocr_content', '')
                    has_ocr = bool(ocr_content and ocr_content.strip())
                    if not has_ocr:
                        should_upload = False
                        skip_reason = "no OCR content"

                if should_upload:
                    try:
                        self.client.add_attachment(
                            issue=issue_key,
                            file_path=file_path
                        )
                        uploaded_count += 1
                        logger.info(
                            f"Successfully uploaded attachment {filename} "
                            f"({content_type}) to {issue_key}"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to upload attachment {filename}: {e}"
                        )
                        skipped_count += 1
                else:
                    skipped_count += 1
                    logger.debug(
                        f"Skipped attachment {filename} ({skip_reason})"
                    )
        except Exception as e:
            logger.error(
                f"Error uploading attachments to {issue_key}: {e}"
            )

        logger.info(
            f"Attachment upload completed for {issue_key}: "
            f"{uploaded_count} uploaded, {skipped_count} skipped"
        )

        return {
            'uploaded_count': uploaded_count,
            'skipped_count': skipped_count
        }

    def _build_jira_summary(
        self,
        email_data: Dict[str, Any]
    ) -> str:
        """
        Build JIRA issue summary from email data dict.

        Args:
            email_data: Dict containing email information

        Returns:
            str: Clean summary for JIRA with prefix and timestamp
        """
        summary = (
            email_data.get('summary_title')
            or email_data.get('subject')
            or 'Email Issue'
        )
        logger.debug(f"Base summary extracted: '{summary[:50]}...'")

        prefix = self.summary_prefix or ''
        logger.debug(f"Summary prefix configured: '{prefix}'")

        if self.summary_timestamp:
            timestamp = datetime.now().strftime("%Y%m%d")
            prefix = f"{prefix}[{timestamp}]"
            logger.debug(f"Added timestamp to prefix: '{prefix}'")

        final_summary = f"{prefix}{summary}"
        logger.debug(
            f"Final summary before cleaning: '{final_summary[:100]}...'"
        )

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

    def _process_embedded_images(
        self,
        llm_content: str,
        attachments: List[Dict[str, Any]]
    ) -> str:
        """
        Process embedded images from attachment data dicts.

        Args:
            llm_content: The LLM processed content
            attachments: List of image attachment dicts

        Returns:
            Processed content with JIRA image format and OCR LLM results
        """
        if not llm_content:
            logger.debug("No LLM content to process for embedded images")
            return ''

        logger.debug(
            f"Processing embedded images in {len(llm_content)} "
            f"characters of LLM content"
        )

        ocr_llm_map = {}
        for att in attachments:
            llm_content_att = att.get('llm_content', '')
            if llm_content_att and llm_content_att.strip():
                filename = (
                    att.get('safe_filename')
                    or att.get('filename', '')
                )
                ocr_llm_map[filename] = llm_content_att

        logger.debug(
            f"Found {len(ocr_llm_map)} attachments with OCR LLM content: "
            f"{list(ocr_llm_map.keys())}"
        )

        def replacer(match):
            fname = match.group(1)
            ocr_llm_text = ocr_llm_map.get(fname)

            jira_image = f"!{fname}|width=600!"

            if ocr_llm_text:
                logger.debug(
                    f"Replaced [IMAGE: {fname}] with JIRA format + "
                    f"OCR LLM content"
                )
                return f"{jira_image}\n\n{ocr_llm_text}\n"
            else:
                logger.debug(
                    f"Replaced [IMAGE: {fname}] with JIRA format only "
                    f"(no OCR LLM content)"
                )
                return jira_image

        processed_content = re.sub(
            r"\[IMAGE:\s*([\w@.\-]+)\]",
            replacer,
            llm_content
        )

        logger.info(
            f"Processed embedded images: "
            f"{len(processed_content)} characters output"
        )
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
        attachments: List[Dict[str, Any]],
        embedded_filenames: set
    ) -> list:
        """
        Process images from attachment dicts that are not embedded.

        Args:
            attachments: List of image attachment dicts
            embedded_filenames: Set of filenames already embedded in content

        Returns:
            List of formatted image content strings
        """
        unembedded_images = []

        for attachment in attachments:
            jira_filename = (
                attachment.get('safe_filename')
                or attachment.get('filename', '')
            )

            llm_content = attachment.get('llm_content', '')
            if (jira_filename not in embedded_filenames
                    and llm_content and llm_content.strip()):

                image_content = []
                image_content.append(f"**Image: {jira_filename}**")
                image_content.append(f"!{jira_filename}|width=600!")

                if llm_content:
                    image_content.append(f"[OCR Result]\n{llm_content}")

                unembedded_images.append("\n".join(image_content))

        return unembedded_images

    def _build_description(
        self,
        email_data: Dict[str, Any],
        attachments: List[Dict[str, Any]],
        summary_only: bool = False
    ) -> str:
        """
        Build comprehensive description from email data and attachments.

        Args:
            email_data: Dict containing email information
            attachments: List of attachment dicts
            summary_only: If True, only return summary content

        Returns:
            str: Formatted description ready for JIRA
        """
        email_id = email_data.get('id')
        logger.debug(
            f"Building description for email {email_id} "
            f"(summary_only={summary_only})"
        )
        content_parts = []

        summary_content = email_data.get('summary_content', '')
        if summary_content and summary_content.strip():
            content_parts.append(summary_content.strip())
            logger.debug(
                f"Added summary content: {len(summary_content)} characters"
            )
        else:
            logger.debug("No summary content available")

        if summary_only:
            combined = "\n".join(content_parts) if content_parts else ""
            logger.info(
                f"Built summary-only description: "
                f"{len(combined)} characters total"
            )
            return combined

        content_parts.append("\n---\n")

        llm_content = email_data.get('llm_content', '')
        if llm_content and llm_content.strip():
            logger.debug(
                f"Processing LLM content: {len(llm_content)} characters"
            )

            image_attachments = [
                att for att in attachments if att.get('is_image', False)
            ]
            llm_content_with_images = self._process_embedded_images(
                llm_content,
                image_attachments
            )
            content_parts.append(llm_content_with_images)
            logger.debug(
                f"Added LLM content with images: "
                f"{len(llm_content_with_images)} characters"
            )
        else:
            logger.debug("No LLM content available")

        content_parts.append("\n---\n")

        embedded_filenames = self._get_embedded_filenames(llm_content or '')
        logger.debug(f"Found embedded filenames: {embedded_filenames}")

        image_attachments = [
            att for att in attachments if att.get('is_image', False)
        ]
        unembedded_images = self._process_unembedded_images(
            image_attachments,
            embedded_filenames
        )
        if unembedded_images:
            content_parts.append("\n\n".join(unembedded_images))
            logger.debug(f"Added {len(unembedded_images)} unembedded images")
        else:
            logger.debug("No unembedded images to add")

        combined = "\n".join(content_parts)
        logger.info(f"Built description: {len(combined)} characters total")

        return combined

    def _process_description_with_llm(
        self,
        description_content: str,
        force: bool = False
    ) -> str:
        """
        Process description with LLM (stateless version).

        Args:
            description_content: Description content to process
            force: If True, force LLM processing

        Returns:
            Processed description
        """
        if not self.description_prompt or not self.description_prompt.strip():
            logger.info("No description prompt configured, using original")
            return description_content

        if not force:
            logger.debug("Not forcing LLM, using original description")
            return description_content

        try:
            logger.info(
                f"Calling LLM for description with "
                f"{len(description_content)} characters of content"
            )
            llm_result = call_llm(self.description_prompt, description_content)
            llm_result = llm_result.strip()

            if llm_result:
                logger.info("LLM processing successful for description")
                return llm_result
            else:
                logger.warning("LLM returned empty result for description")
                return description_content
        except Exception as e:
            logger.error(f"Failed to process description with LLM: {e}")
            return description_content

    def _determine_project_key(
        self,
        content: str,
        force: bool = False
    ) -> str:
        """
        Determine project key using LLM (stateless version).

        Args:
            content: Content to analyze
            force: If True, force LLM processing

        Returns:
            Project key
        """
        if not self.project_prompt or not self.project_prompt.strip():
            logger.info(
                f"No project prompt configured, "
                f"using default: {self.project_key}"
            )
            return self.project_key

        if not force:
            logger.debug("Not forcing LLM, using default project key")
            return self.project_key

        try:
            logger.info(
                f"Calling LLM for project key with "
                f"{len(content)} characters of content"
            )
            llm_result = call_llm(self.project_prompt, content)
            llm_result = llm_result.strip()

            if llm_result:
                if llm_result in self.allow_project_keys:
                    logger.info(f"LLM selected valid project key: {llm_result}")
                    return llm_result
                else:
                    logger.warning(
                        f"LLM returned invalid project key '{llm_result}', "
                        f"not in allowed list: {self.allow_project_keys}. "
                        f"Using default: {self.project_key}"
                    )
            else:
                logger.warning("LLM returned empty result for project key")
        except Exception as e:
            logger.error(f"Failed to determine project key with LLM: {e}")

        return self.project_key

    def _determine_assignee(
        self,
        content: str,
        force: bool = False
    ) -> str:
        """
        Determine assignee using LLM (stateless version).

        Args:
            content: Content to analyze
            force: If True, force LLM processing

        Returns:
            Assignee
        """
        if not self.assignee_prompt or not self.assignee_prompt.strip():
            logger.info(
                f"No assignee prompt configured, "
                f"using default: {self.assignee}"
            )
            return self.assignee

        if not force:
            logger.debug("Not forcing LLM, using default assignee")
            return self.assignee

        try:
            logger.info(
                f"Calling LLM for assignee with "
                f"{len(content)} characters of content"
            )
            llm_result = call_llm(self.assignee_prompt, content)
            llm_result = llm_result.strip()

            if llm_result:
                if llm_result in self.allow_assignees:
                    logger.info(f"LLM selected valid assignee: {llm_result}")
                    return llm_result
                else:
                    logger.warning(
                        f"LLM returned invalid assignee '{llm_result}', "
                        f"not in allowed list: {self.allow_assignees}. "
                        f"Using default: {self.assignee}"
                    )
            else:
                logger.warning("LLM returned empty result for assignee")
        except Exception as e:
            logger.error(f"Failed to determine assignee with LLM: {e}")

        return self.assignee
