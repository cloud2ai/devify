"""
JIRA Issue Handler for external system integration.

This module handles JIRA-specific operations without any state management.
It's purely focused on JIRA API interactions.

Design principle: This handler should NOT use Django ORM models.
All data should be passed as dictionaries to avoid database dependencies.

Configuration Structure:
======================

The handler expects a configuration dictionary with the following structure:

{
    "jira": {
        "url": "https://your-jira-instance.com/",
        "username": "your-username",
        "api_token": "your-api-token"
    },
    "language": "Chinese",
    "fields": {
        "project_key_config": {
            "use_llm": false,
            "jira_field": "project",
            "default": "REQ"
        },
        "issue_type_config": {
            "use_llm": false,
            "jira_field": "issuetype",
            "default": "New Feature"
        },
        "priority_config": {
            "use_llm": false,
            "jira_field": "priority",
            "default": "High"
        },
        "summary_config": {
            "prefix": "[AI]",
            "use_llm": true,
            "jira_field": "summary",
            "prompt_template": "Generate summary based on email content..."
        },
        "description_config": {
            "use_llm": false,
            "jira_field": "description",
            "convert_to_jira_wiki": true
        },
        "components": {
            "fetch_from_api": true,
            "jira_field": "components",
            "projects": ["REQ"]
        },
        "epic_link": {
            "fetch_from_api": true,
            "jira_field": "customfield_10014",
            "jql_filter": "issuetype = Epic"
        }
    }
}

Field Configuration Options:
============================

1. Static Fields (use_llm=false, fetch_from_api=false):
   - Used for fields with fixed values
   - Required: jira_field, default
   - Example: project_key_config, issue_type_config, priority_config

2. LLM Fields (use_llm=true):
   - Fields processed by LLM for dynamic content generation
   - Required: jira_field, prompt_template
   - Optional: prefix, suffix, max_length
   - Example: summary_config, description_config

3. API Fields (fetch_from_api=true):
   - Fields that fetch data from JIRA API
   - Required: jira_field
   - Optional: projects (for components), jql_filter (for epics)
   - Example: components, epic_link

Important Notes:
===============

- Field names must end with "_config" for static/LLM fields
- API fields can use simple names (e.g., "components", "epic_link")
- The "default" value is used as fallback when processing fails
- Project key is extracted from project_key_config.default
- All fields are categorized during initialization for efficient processing
"""

import json
import logging
import os
import time
from typing import Any, Dict, List

from devtoolbox.api_clients.jira_client import JiraClient

from ..llm import call_llm
from .jira_utils import (
    build_summary_field, get_grouped_configs, preprocess_api_data,
    build_description_field, build_field_prompt, remove_emoji,
    DEFAULT_LANGUAGE
)

logger = logging.getLogger(__name__)


# Base prompt template for LLM prompt generation
BASE_PROMPT = (
    "You are a Jira issue assistant. Analyze the provided content and output "
    "a JSON response.\n\n"
    "IMPORTANT:\n"
    "- Output must be valid JSON format\n"
    "- JSON keys MUST remain in English (do not translate keys)\n"
    "- All fields must be present in the response"
)

# Retry configuration for JIRA API calls
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds

# Default JQL for fetching epics
DEFAULT_EPIC_JQL = "project = {project_key} AND issuetype = Epic"


class JiraIssueHandler:
    """
    Handler for JIRA operations, such as creating issues and
    uploading attachments.

    This class is purely focused on JIRA operations and doesn't
    handle any state management or workflow logic.

    Attributes:
        client (JiraClient): JIRA API client instance
        native_client (JIRA): Native JIRA client for direct access to all
            methods

    Note:
        Use `native_client` to access any JIRA API method not directly
        supported
        by the JiraClient wrapper. This provides full access to the underlying
        JIRA Python library functionality.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize JiraIssueHandler with configuration.

        Args:
            config: Configuration dictionary containing "jira" and "fields"
                    sections.
                    See module docstring for detailed configuration structure.
        """
        # Extract jira connection config
        jira_config = config.get("jira", {})
        self.jira_url = jira_config.get("url")
        self.username = jira_config.get("username")
        self.api_token = jira_config.get("api_token")

        # Language for LLM output
        self.language = config.get("language", DEFAULT_LANGUAGE)

        # Store raw field configuration for processing during issue creation
        self.fields_config = config.get("fields", {})

        # Format field configurations once during initialization
        self.formatted_configs = get_grouped_configs(self.fields_config)

        # Get default project information from field configuration
        project_config = self.fields_config.get("project_key_config", {})
        self.default_project_key = project_config.get("default", "REQ")
        logger.info(f"Default project key: {self.default_project_key}")

        # Create JiraClient for API operations (after all config is processed)
        self.client = JiraClient(
            jira_url=self.jira_url,
            username=self.username,
            password=self.api_token
        )

        # Expose native JIRA client for direct access to all methods
        self.native_client = self.client.client

    def get_issue_url(self, issue_key: str) -> str:
        """
        Get the full URL for a JIRA issue.

        Args:
            issue_key: JIRA issue key (e.g., "REQ-123")

        Returns:
            str: Full URL to the JIRA issue
        """
        return f"{self.jira_url}browse/{issue_key}"

    def _fetch_components(self, project_key: str) -> List[str]:
        """
        Fetch components from a JIRA project with retry mechanism.

        Args:
            project_key: Project key to fetch components from

        Returns:
            List of component names
        """
        logger.info(f"Fetching components from project: {project_key}")

        for attempt in range(MAX_RETRIES):
            try:
                components = self.native_client.project_components(
                    project_key
                )
                component_names = [comp.name for comp in components]
                logger.info(f"Found {len(component_names)} "
                            f"components in {project_key}")
                return component_names

            except Exception as e:
                logger.warning(
                    f"Attempt {attempt + 1}/{MAX_RETRIES} failed to fetch "
                    f"components from {project_key}: {e}"
                )
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error(
                        f"Failed to fetch components after {MAX_RETRIES} "
                        f"attempts"
                    )
                    return []

    def _fetch_epics(self, project_key: str, jql_filter: str = None) -> list:
        """
        Fetch epics from a JIRA project using JQL query with retry mechanism.
        Fetches all pages to get complete list.

        Args:
            project_key: Jira project key
            jql_filter: Custom JQL query to filter epics (optional)

        Returns:
            List of epic dictionaries with "key" and "summary" fields
        """
        logger.info(f"Fetching epics from project: {project_key}")

        for attempt in range(MAX_RETRIES):
            try:
                # Determine JQL query to use
                if jql_filter:
                    jql_query = jql_filter
                else:
                    jql_query = DEFAULT_EPIC_JQL.format(
                        project_key=project_key
                    )

                logger.info(f"Using JQL: {jql_query}")

                # Fetch all pages
                epic_list = []
                start_at = 0
                max_results_per_page = 50

                while True:
                    issues = self.native_client.search_issues(
                        jql_query,
                        startAt=start_at,
                        maxResults=max_results_per_page
                    )

                    if not issues:
                        break

                    page_epics = [
                        {"key": epic.key, "summary": epic.fields.summary}
                        for epic in issues
                    ]
                    epic_list.extend(page_epics)

                    logger.debug(
                        f"Fetched page with {len(issues)} issues "
                        f"(total: {len(epic_list)})"
                    )

                    # Check if there are more results
                    if len(issues) < max_results_per_page:
                        break

                    start_at += max_results_per_page

                logger.info(
                    f"Found {len(epic_list)} epics total in {project_key}"
                )

                # Log first few epic keys for debugging
                if epic_list:
                    epic_keys = [
                        epic['key'] for epic in epic_list[:5]
                    ]
                    logger.debug(f"Epic keys: {epic_keys}")
                else:
                    logger.warning(
                        f"No epics found with provided JQL query"
                    )

                return epic_list

            except Exception as e:
                logger.warning(
                    f"Attempt {attempt + 1}/{MAX_RETRIES} failed to fetch "
                    f"epics from {project_key}: {e}"
                )
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error(
                        f"Failed to fetch epics after {MAX_RETRIES} "
                        f"attempts", exc_info=True
                    )
                    return []


    def create_issue(
        self,
        issue_data: Dict[str, Any],
        email_data: Dict[str, Any],
        attachments: List[Dict[str, Any]],
        force: bool = False
    ) -> str:
        """
        Create a JIRA issue from pure data dictionaries (no ORM objects).

        Args:
            issue_data: Dict containing issue information
            email_data: Dict containing email information
            attachments: List of attachment dicts
            force: If True, force LLM processing

        Returns:
            str: JIRA issue key (e.g., "REQ-123")

        Raises:
            Exception: If JIRA issue creation fails
        """
        try:
            summary_title = email_data["summary_title"]
            summary_content = email_data.get("summary_content", "")
            summary_data = email_data.get("summary_data")
            todos = email_data.get("todos")
            llm_content = email_data.get("llm_content", "")
            language = email_data.get("language", "en")

            logger.info(
                f"Starting JIRA issue creation: '{summary_title[:50]}...' "
                f"(force={force})"
            )

            # ========================================
            # Stage 1: Process static fields
            # ========================================
            logger.info("Stage 1: Processing static fields")
            jira_fields = self._process_static_fields(
                summary_title=summary_title,
                summary_content=summary_content,
                llm_content=llm_content,
                attachments=attachments,
                force=force,
                summary_data=summary_data,
                todos=todos,
                language=language
            )

            # ========================================
            # Stage 2: Process API fields
            # ========================================
            logger.info("Stage 2: Processing API fields")
            self._process_api_fields()

            # ========================================
            # Stage 3: Process LLM fields
            # ========================================
            logger.info("Stage 3: Processing LLM fields")
            llm_data = self._process_llm_fields(
                summary_title=summary_title,
                summary_content=summary_content,
                llm_content=llm_content,
                attachments=attachments,
                force=force,
                summary_data=summary_data,
                todos=todos,
                language=language
            )

            # Merge all field data
            jira_fields.update(llm_data)

            # Extract labels from metadata
            labels = self._extract_labels_from_metadata(email_data)

            # Extract individual parameters for create_issue
            project_key = jira_fields.pop("project", self.default_project_key)
            summary = jira_fields.pop("summary", "No title")
            issue_type = jira_fields.pop("issuetype", "Story")
            description = jira_fields.pop("description", None)
            assignee = jira_fields.pop("assignee", None)
            priority = jira_fields.pop("priority", None)
            components = jira_fields.pop("components", None)
            epic_link = jira_fields.pop("customfield_10014", None)

            # Remove any other fields that might conflict
            # These are already handled by explicit parameters above
            extra_fields = {}
            for key, value in jira_fields.items():
                if key not in [
                    "project", "summary", "issuetype", "description",
                    "assignee", "priority", "components",
                    "customfield_10014", "epic_link"
                ]:
                    extra_fields[key] = value

            # Log key fields to be created
            logger.info(
                f"Creating JIRA issue: {summary} "
                f"(Project: {project_key}, Type: {issue_type}, "
                f"Epic: {epic_link}, Components: {components}, "
                f"Labels: {labels})"
            )

            # Create the issue with explicit parameters
            issue_key = self.client.create_issue(
                project_key=project_key,
                summary=summary,
                issue_type=issue_type,
                description=description,
                assignee=assignee,
                priority=priority,
                components=components,
                epic_link=epic_link,
                labels=labels if labels else None,
                **extra_fields  # Pass any remaining extra fields
            )

            logger.info(
                f"Successfully created JIRA issue: {issue_key} "
                f"for '{summary_title[:50]}...'"
            )
            return issue_key

        except Exception as e:
            logger.error(
                f"Failed to create JIRA issue for '{summary_title}...': {e}",
                exc_info=True
            )
            raise

    def _extract_labels_from_metadata(
        self,
        email_data: Dict[str, Any]
    ) -> List[str]:
        """
        Extract JIRA labels from email metadata.

        All metadata fields are converted to labels.
        List values are expanded, other values are converted to strings.

        Args:
            email_data: Email data dictionary containing metadata

        Returns:
            List[str]: List of labels extracted from metadata
        """
        labels = []
        metadata = email_data.get("metadata", {})

        if not metadata:
            return labels

        # Iterate through all metadata fields
        for key, value in metadata.items():
            if not value:
                continue

            # Handle list values (e.g., keywords, timeline, participants)
            if isinstance(value, list):
                for item in value:
                    if item:
                        # Remove spaces and emojis for JIRA label compatibility
                        label = str(item).replace(' ', '')
                        label = remove_emoji(label)
                        labels.append(label)
            # Handle other values (e.g., category, scene)
            else:
                # Remove spaces and emojis for JIRA label compatibility
                label = str(value).replace(' ', '')
                label = remove_emoji(label)
                labels.append(label)

        logger.debug(f"Extracted {len(labels)} labels from metadata")
        return labels

    def _process_static_fields(
        self,
        summary_title: str,
        summary_content: str,
        llm_content: str,
        attachments: List[Dict[str, Any]],
        force: bool,
        summary_data: Dict[str, Any] | None = None,
        todos: List[Dict[str, Any]] | None = None,
        language: str = 'en'
    ) -> Dict[str, Any]:
        """
        Process static fields and return a simple key-value dictionary.

        Args:
            summary_title: Issue summary title
            summary_content: Issue summary content (fallback)
            llm_content: LLM processed content
            attachments: List of attachments
            force: Whether to force processing
            summary_data: Structured summary data (preferred)
            todos: List of TODO items (preferred)
            language: Language for section headings

        Returns:
            Dict[str, Any]: Simple key-value dictionary for JIRA fields
        """
        jira_fields = {}

        # Get all static fields
        static_fields = self.formatted_configs["static_fields"]

        for field_name, field_config in static_fields.items():
            jira_field = field_config["jira_field"]

            # Process fields with default values
            if field_config.get("default"):
                jira_fields[jira_field] = field_config["default"]

            # Special handling for summary field
            elif field_name == "summary":
                summary_config = self.fields_config.get("summary_config", {})
                jira_fields[jira_field] = build_summary_field(
                    summary=summary_title,
                    prefix=summary_config.get("prefix", "[AI]"),
                    add_timestamp=summary_config.get("add_timestamp", False)
                )
                logger.info(f"Generated summary: {jira_fields[jira_field]}")

            # Special handling for description field
            elif field_name == "description":
                description_config = self.fields_config.get(
                    "description_config", {})
                convert_to_jira_wiki = description_config.get(
                    "convert_to_jira_wiki", True)

                jira_fields[jira_field] = build_description_field(
                    summary_content=summary_content,
                    llm_content=llm_content,
                    attachments=attachments,
                    convert_to_jira_wiki=convert_to_jira_wiki,
                    summary_data=summary_data,
                    todos=todos,
                    language=language
                )

        logger.info(f"Processed {len(jira_fields)} static fields")
        return jira_fields

    def _process_api_fields(self) -> None:
        """
        Stage 2: Process API fields by fetching data from JIRA and storing
        them in llm_fields for unified processing.

        This stage handles:
        - Components fetching → store in llm_fields.api_data
        - Epic data fetching → store in llm_fields.api_data
        - Other API-dependent fields → store in llm_fields.api_data
        """
        # Get API fields
        api_fields = self.formatted_configs["api_fields"]

        for field_name, field_config in api_fields.items():
            jira_field = field_config["jira_field"]
            logger.debug(
                f"Processing API field: {field_name} "
                f"(jira_field={jira_field})"
            )

            try:
                if field_name == "components":
                    # Fetch components and store in llm_fields
                    components = self._fetch_components(
                        self.default_project_key)
                    self._save_api_data(field_name, components)

                elif field_name == "epic_link":
                    # Fetch epics and store in llm_fields
                    jql_filter = field_config.get("jql_filter")
                    epics = self._fetch_epics(
                        self.default_project_key, jql_filter)
                    self._save_api_data(field_name, epics)

                else:
                    # Handle other API fields - configuration error
                    raise ValueError(
                        f"Unknown API field: {field_name}. "
                        f"Check configuration.")

            except Exception as e:
                logger.warning(f"Failed to fetch API data for "
                               f"{field_name}: {e}")
                default_value = field_config.get("default", [])
                self._save_api_data(field_name, default_value)

        logger.info(f"Stage 2 completed: {len(api_fields)} API fields "
                    f"processed")

    def _save_api_data(self, field_name: str, api_data: Any) -> None:
        """
        Save API data for LLM processing.
        Preprocess data into LLM-ready format.

        Args:
            field_name: Name of the field (clean name, e.g., "components",
                        "epic_link")
            api_data: API fetched data to store
        """
        # Store API data in llm_fields (which will be used for LLM processing)
        llm_fields = self.formatted_configs.get("llm_fields", {})

        # Preprocess data and store in allow_values
        processed_data = preprocess_api_data(field_name, api_data)

        # Store in llm_fields
        if field_name in llm_fields:
            llm_fields[field_name]["allow_values"] = processed_data
        else:
            logger.warning(
                f"Field {field_name} not found in llm_fields. "
                f"Available keys: {list(llm_fields.keys())}"
            )

    def _build_llm_prompt(
        self,
        summary_title: str,
        summary_content: str,
        llm_content: str,
        llm_fields: Dict[str, Any]
    ) -> str:
        """
        Build LLM prompt for field analysis.

        Args:
            summary_title: Issue summary title
            summary_content: Issue summary content
            llm_content: LLM processed content
            llm_fields: LLM field configurations (with api_data from API)

        Returns:
            str: Complete prompt for LLM
        """
        base_instruction = BASE_PROMPT

        json_schema = {}
        field_instructions = []

        for field_name, field_config in llm_fields.items():
            jira_field = field_config["jira_field"]
            default_value = field_config.get("default", "")
            json_schema[jira_field] = (
                [] if isinstance(default_value, list) else ""
            )

            # Get allow_values from field_config (populated by API stage)
            allow_values = field_config.get("allow_values", [])

            prompt = build_field_prompt(
                field_config,
                allow_values,
                self.language,
                field_name
            )
            field_instructions.append(f"- {jira_field}: {prompt}")

        if not json_schema:
            return ""

        json_schema_str = json.dumps(
            json_schema, indent=2, ensure_ascii=False
        )
        instructions_text = "\n".join(field_instructions)

        # Orgnize summary content for JIRA fields generate
        content_text = f"Title: {summary_title}\n\nSummary: {summary_content}"

        prompt = f"""{base_instruction}

Content to analyze:
{content_text}

Output JSON Schema:
{json_schema_str}

Field Instructions:
{instructions_text}

If a field value cannot be determined, use the default value
from configuration."""

        return prompt

    def _validate_llm_response(
        self,
        llm_response: Dict[str, Any],
        llm_fields: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate and map LLM response to field names.

        Args:
            llm_response: Raw response from LLM
            llm_fields: LLM field configurations

        Returns:
            Dict[str, Any]: Validated field values
        """
        validated_data = {}

        for field_name, field_config in llm_fields.items():
            jira_field = field_config["jira_field"]
            default_value = field_config.get("default")
            allow_values = field_config.get("allow_values", [])

            if jira_field not in llm_response:
                logger.warning(
                    f"Field {jira_field} not in LLM response, "
                    f"skipping field"
                )
                continue

            value = llm_response[jira_field]

            # Check if value is empty
            is_empty = (
                not value or
                (isinstance(value, str) and not value.strip())
            )

            # Handle empty or invalid values
            if is_empty:
                if default_value:
                    logger.warning(
                        f"LLM returned empty value for {jira_field}. "
                        f"Using default value: {default_value}"
                    )
                    value = default_value
                else:
                    logger.debug(
                        f"Skipping empty value for {jira_field} "
                        f"(no default configured)"
                    )
                    continue
            elif allow_values:
                # Validate against allow_values
                if isinstance(value, list):
                    normalized_value = [str(item).strip() for item in value]
                    normalized_allow = [str(av).strip() for av in allow_values]
                    is_valid = all(
                        item in normalized_allow for item in normalized_value
                    )
                else:
                    normalized_value = str(value).strip()
                    normalized_allow = [str(av).strip() for av in allow_values]
                    is_valid = normalized_value in normalized_allow

                if not is_valid:
                    if default_value:
                        logger.warning(
                            f"LLM returned invalid value '{value}' for "
                            f"{jira_field}. Available options: {allow_values}. "
                            f"Using default value: {default_value}"
                        )
                        value = default_value
                    else:
                        logger.warning(
                            f"LLM returned invalid value '{value}' for "
                            f"{jira_field}. Available options: {allow_values}. "
                            f"Default not configured, skipping field."
                        )
                        continue

            # Special handling for components field
            # If LLM returns a string instead of list, convert it
            if field_name == "components" and isinstance(value, str):
                if "," in value:
                    value = [item.strip() for item in value.split(",")]
                else:
                    value = [value]

            # Store validated value
            validated_data[jira_field] = value
            logger.debug(f"Mapped {jira_field}: {value}")

        return validated_data

    def _process_llm_fields(
        self,
        summary_title: str,
        summary_content: str,
        llm_content: str,
        attachments: List[Dict[str, Any]],
        force: bool,
        summary_data: Dict[str, Any] | None = None,
        todos: List[Dict[str, Any]] | None = None,
        language: str = 'en'
    ) -> Dict[str, Any]:
        """
        Stage 3: Process LLM fields using AI analysis.

        This stage handles:
        - Building LLM prompts with API data (now stored in api_data)
        - Calling LLM for field analysis
        - Processing LLM responses
        - Returning validated field data

        Args:
            summary_title: Issue summary title
            summary_content: Issue summary content
            llm_content: LLM processed content
            attachments: List of attachment dicts
            force: Whether to force processing

        Returns:
            Dict[str, Any]: LLM processed field data
        """
        # Get LLM fields
        llm_fields = self.formatted_configs.get("llm_fields", {})

        if not llm_fields:
            logger.info("No LLM fields to process")
            return {}

        # ========================================
        # Build LLM prompt with API data (now stored in allow_values)
        # ========================================
        prompt = self._build_llm_prompt(
            summary_title=summary_title,
            summary_content=summary_content,
            llm_content=llm_content,
            llm_fields=llm_fields
        )
        logger.debug(f"LLM prompt: {prompt}")

        # ========================================
        # Call LLM for analysis
        # ========================================
        try:
            llm_response = call_llm(
                prompt=prompt,
                content=summary_content,
                json_mode=True,
                max_retries=3
            )

            if not llm_response or not isinstance(llm_response, dict):
                logger.warning("LLM returned invalid result")
                validated_data = {}
            else:
                validated_data = self._validate_llm_response(
                    llm_response, llm_fields)
        except Exception as e:
            logger.error(f"LLM processing failed: {e}")
            validated_data = {}

        # ========================================
        # Post-process LLM fields
        # ========================================
        # Note: summary and description are processed in static fields stage
        # Only LLM-selected fields are processed here

        logger.info(f"Stage 3 completed: {len(validated_data)} "
                    f"LLM fields processed")
        return validated_data

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
                filename = attachment.get("filename", "unknown")
                content_type = attachment.get("content_type", "")
                is_image = attachment.get("is_image", False)
                file_path = attachment.get("file_path", "")
                file_size = attachment.get("file_size", 0)

                # Only process image attachments
                if not is_image:
                    logger.debug(
                        f"Skipping non-image attachment: {filename}"
                    )
                    skipped_count += 1
                    continue

                logger.info(
                    f"Processing image attachment: {filename} "
                    f"(type: {content_type}, size: {file_size} bytes)"
                )

                logger.debug(
                    f"Attachment fields: {list(attachment.keys())}"
                )

                if not os.path.exists(file_path):
                    logger.warning(
                        f"Attachment file not found: {file_path}"
                    )
                    skipped_count += 1
                    continue

                should_upload = True
                skip_reason = ""

                if is_image:
                    # Check for LLM content (processed OCR content)
                    llm_content = attachment.get("llm_content", "")
                    has_llm_content = bool(llm_content and llm_content.strip())

                    # Also check for OCR content for backward compatibility
                    ocr_content = attachment.get("ocr_content", "")
                    has_ocr = bool(ocr_content and ocr_content.strip())

                    if not has_llm_content and not has_ocr:
                        should_upload = False
                        skip_reason = "no LLM or OCR content"

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
            "uploaded_count": uploaded_count,
            "skipped_count": skipped_count
        }
