"""
JIRA utility functions for field processing and data manipulation.

This module contains helper functions for JIRA field processing,
data validation, and utility operations that are used by the main
JiraIssueHandler class.
"""

import logging
import re
from typing import Dict, Any, List, Optional

from django.core.cache import cache

from .md_to_jira import to_jira_wiki

# Default language for LLM output
DEFAULT_LANGUAGE = "Chinese"

# Prompt templates for LLM field processing
SELECTION_PROMPT = (
    "Select the most appropriate value from the provided data that best "
    "matches the requirements and conditions. If uncertain, do not make "
    "random choices"
)

GENERATION_PROMPT_TEMPLATE = (
    "Generate appropriate value based on the content in {language}"
)

logger = logging.getLogger(__name__)


def remove_emoji(text: str) -> str:
    """
    Remove emoji and emoticon characters from text.

    Args:
        text: Input text that may contain emojis

    Returns:
        str: Text with emojis removed
    """
    if not text:
        return text

    # More specific emoji removal pattern
    # Only remove actual emoji characters, not all extended unicode
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons (😀-🙏)
        "\U0001F300-\U0001F5FF"  # symbols & pictographs (🌀-🗿)
        "\U0001F680-\U0001F6FF"  # transport & map symbols (🚀-🛿)
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002702-\U000027B0"   # dingbats
        "\U00002600-\U000027BF"   # miscellaneous symbols
        "\U0001f900-\U0001f9ff"  # supplemental symbols
        "\U0001fa00-\U0001fa6f"   # chess symbols
        "]",
        flags=re.UNICODE
    )

    # Remove only emoji characters, not whole words
    cleaned_text = emoji_pattern.sub('', text)

    # Clean up multiple consecutive spaces (but preserve line breaks)
    # Replace 3+ spaces with 2 spaces, and 2 spaces with 1 space
    # This preserves single line breaks while cleaning up excessive spaces
    cleaned_text = re.sub(r'   +', '  ', cleaned_text)
    cleaned_text = re.sub(r'  ', ' ', cleaned_text)

    return cleaned_text


def build_summary_field(
    summary: str,
    prefix: str = "[AI]",
    add_timestamp: bool = False
) -> str:
    """
    Build the final summary field with prefix and optional timestamp.

    Args:
        summary: Base summary text
        prefix: Prefix to add to summary
        add_timestamp: Whether to add timestamp

    Returns:
        str: Formatted summary field
    """
    if not summary:
        return summary

    # Clean the summary
    cleaned_summary = remove_emoji(summary)

    # Build final summary with prefix and optional timestamp
    if prefix:
        # Add timestamp if requested (format: YYYY-MM-DD)
        if add_timestamp:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d")
            final_summary = f"{prefix}[{timestamp}]{cleaned_summary}"
        else:
            final_summary = f"{prefix}{cleaned_summary}"
    else:
        final_summary = cleaned_summary

    return final_summary


def get_grouped_configs(fields_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get field configurations grouped by processing type.

    Args:
        fields_config: Raw field configuration dictionary

    Returns:
        Dict[str, Any]: Grouped field configurations organized by type:
            - static_fields: Fields with use_llm=false, fetch_from_api=false
            - llm_fields: Fields with use_llm=true
            - api_fields: Fields with fetch_from_api=true
            - all_fields: All fields for reference

    Output format:
    {
        "static_fields": {
            "project_key_config": {
                "jira_field": "project", "default": "REQ",
                "use_llm": false, "fetch_from_api": false
            }
        },
        "llm_fields": {
            "summary_config": {
                "jira_field": "summary", "prompt_template": "...",
                "use_llm": true, "fetch_from_api": false
            }
        },
        "api_fields": {
            "components": {
                "jira_field": "components",
                "use_llm": false, "fetch_from_api": true
            }
        },
        "all_fields": { /* All fields for reference */ }
    }

    Classification Rules:
    - Static: use_llm=false AND fetch_from_api=false
      → {jira_field, default, use_llm, fetch_from_api}
    - LLM: use_llm=true
      → {jira_field, prompt_template, use_llm, fetch_from_api}
    - API: fetch_from_api=true
      → {jira_field, use_llm, fetch_from_api, [additional_config]}
    """
    categorized = {
        "static_fields": {},      # Fields with static values
        "llm_fields": {},         # Fields requiring LLM processing
        "api_fields": {},         # Fields requiring API data fetching
        "all_fields": {}          # All fields for reference
    }

    for field_name, field_config in fields_config.items():
        # Remove _config suffix for clean field name if exists
        if field_name.endswith("_config"):
            clean_field_name = field_name.replace("_config", "")
        else:
            clean_field_name = field_name

        jira_field = field_config.get("jira_field", clean_field_name)
        use_llm = field_config.get("use_llm", False)
        fetch_from_api = field_config.get("fetch_from_api", False)

        default_field_data = {
            "allow_values": [],
            "prompt": "",
            "default": "",
            "jira_field": jira_field,
            "use_llm": use_llm,
            "fetch_from_api": fetch_from_api
        }
        field_data = default_field_data.copy()
        field_data.update(field_config)

        # Store in all_fields for reference
        categorized["all_fields"][clean_field_name] = field_data

        # Categorize by processing type
        if fetch_from_api:
            categorized["api_fields"][clean_field_name] = field_data
            # API fields need LLM processing to select from options
            categorized["llm_fields"][clean_field_name] = field_data

        elif use_llm:
            categorized["llm_fields"][clean_field_name] = field_data

        else:
            # Static fields
            categorized["static_fields"][clean_field_name] = field_data

    return categorized


def preprocess_api_data(field_name: str, api_data: Any) -> List[str]:
    """
    Preprocess API data into LLM-ready format.

    Args:
        field_name: Name of the field
        api_data: Raw API data

    Returns:
        List[str]: Processed data ready for LLM prompt
    """
    if field_name == "components":
        # Components: simple list of names
        return api_data

    elif field_name == "epic_link":
        # Epics: show key and summary
        return [
            f"{item.get('key', '')} ({item.get('summary', '')})"
            for item in api_data
        ]

    else:
        # Default: convert to list of strings
        return [str(item) for item in api_data]


def get_embedded_files(llm_content: str) -> set:
    """
    Extract embedded image filenames from processed content.

    Args:
        llm_content: The processed content (after embed_images)

    Returns:
        Set of embedded image filenames
    """
    if not llm_content:
        return set()

    """
    Extract from Jira image format: !filename|width=600!
    This works after embed_images has converted [IMAGE: filename]
    to Jira format.
    """
    embedded_matches = re.findall(
        r"!([\w@.\-]+)\|width=600!", llm_content
    )
    return set(embedded_matches)


def build_field_prompt(
    field_config: Dict[str, Any],
    allow_values: List[str],
    language: str,
    field_name: str = None
) -> str:
    """
    Build prompt text for a single field.

    Args:
        field_config: Field configuration dict
        allow_values: Available values (from API or config)
        language: Language for generation prompt
        field_name: Name of the field (for epic detection)

    Returns:
        Prompt text for this field
    """
    # Get custom prompt if provided
    custom_prompt = field_config.get("prompt", "")
    if custom_prompt:
        base_prompt = custom_prompt
    else:
        # Use default prompt based on whether we have options
        if allow_values:
            base_prompt = SELECTION_PROMPT
        else:
            base_prompt = GENERATION_PROMPT_TEMPLATE.format(language=language)

    # Handle different field types
    if not allow_values:
        return base_prompt

    values_str = ", ".join([f'"{v}"' for v in allow_values])

    # Epic link: key (summary) format - return only the key
    if field_name == "epic_link":
        return (
            f"{base_prompt}. Available options: {values_str}. "
            f"IMPORTANT: Each option is in format 'KEY (Summary)'. "
            f"You MUST return only the KEY part (e.g., 'REQ-123'), "
            f"not the full 'KEY (Summary)' string. "
            f"CRITICAL: If the project name is not explicitly mentioned in "
            f"the content, return empty string '' instead of guessing."
        )

    # Other fields (including components): default handling
    return f"{base_prompt}. Available options: {values_str}"


def build_description_field(
    summary_content: str,
    llm_content: str,
    attachments: List[Dict[str, Any]],
    convert_to_jira_wiki: bool
) -> str:
    """
    Build JIRA description field.

    Args:
        summary_content: Email summary content
        llm_content: LLM processed content
        attachments: List of attachment dicts
        convert_to_jira_wiki: Whether to convert to JIRA Wiki format

    Returns:
        Cleaned and formatted description text
    """
    summary_part = build_summary_part(summary_content)
    original_chats_part = build_original_chats_part(
        llm_content,
        attachments
    )
    description_content = f"{summary_part}\n---\n{original_chats_part}"

    processed_description = description_content
    if convert_to_jira_wiki:
        processed_description = to_jira_wiki(processed_description)

    cleaned_description = remove_emoji(processed_description)[:10000]

    return cleaned_description


def build_original_chats_part(
    llm_content: str,
    attachments: List[Dict[str, Any]]
) -> str:
    """
    Build original chats part of description.

    This part combines:
    - Original chat records content (LLM processed)
    - Images with OCR summary information

    Args:
        llm_content: LLM processed content (original chat records)
        attachments: List of attachment dicts (images with OCR)

    Returns:
        Formatted original chats part with images and OCR summaries
    """
    content_parts = []

    # Get image attachments once
    image_attachments = [
        att for att in attachments if att.get("is_image", False)
    ]

    if llm_content and llm_content.strip():
        llm_content_with_images = embed_images(
            llm_content,
            image_attachments
        )
        content_parts.append(llm_content_with_images)

        """
        Extract embedded filenames from PROCESSED content to avoid
        duplicate OCR displays. After embed_images processing,
        [IMAGE: filename] markers have been replaced.
        """
        embedded_filenames = get_embedded_files(llm_content_with_images)
    else:
        embedded_filenames = set()

    unembedded_images = list_unembedded_images(
        image_attachments,
        embedded_filenames
    )

    if unembedded_images:
        content_parts.append("\n\n".join(unembedded_images))

    combined = "\n".join(content_parts)
    return combined


def embed_images(
    llm_content: str,
    attachments: List[Dict[str, Any]]
) -> str:
    """
    Embed images into content.

    Convert [IMAGE: filename] markers to JIRA image format.
    Note: OCR content is already in llm_content from LLM processing,
    so we only replace the marker without adding OCR again.

    Args:
        llm_content: The LLM processed content with [IMAGE: filename] markers
        attachments: List of attachment dicts (not used, kept for interface)

    Returns:
        Content with Jira image format (!filename|width=600!)
    """
    if not llm_content:
        return ""

    def replacer(match):
        fname = match.group(1)
        return f"!{fname}|width=600!"

    return re.sub(
        r"\[IMAGE:\s*([\w@.\-]+)\]",
        replacer,
        llm_content
    )


def build_summary_part(summary_content: str) -> str:
    """
    Build summary part of description.

    Args:
        summary_content: Email summary content

    Returns:
        Formatted summary part without OCR content
    """
    if summary_content and summary_content.strip():
        content = summary_content.strip()

        # Remove OCR section if present (legacy format from summary_node)
        if "--- ATTACHMENT OCR CONTENT ---" in content:
            parts = content.split("--- ATTACHMENT OCR CONTENT ---")
            content = parts[0].strip()

        return content
    else:
        return ""


def list_unembedded_images(
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
            attachment.get("safe_filename")
            or attachment.get("filename", "")
        )

        llm_content = attachment.get("llm_content", "")

        if (jira_filename not in embedded_filenames
                and llm_content and llm_content.strip()):

            image_content = []
            image_content.append(f"**Image: {jira_filename}**")
            image_content.append(f"!{jira_filename}|width=600!")

            if llm_content:
                image_content.append(f"[Image Content]\n{llm_content}")

            unembedded_images.append("\n".join(image_content))

    return unembedded_images
