import json
import logging
from typing import Any, Dict

from json_repair import repair_json

logger = logging.getLogger(__name__)


def parse_json_response(response: str) -> Dict[str, Any]:
    """
    Parse and clean JSON response from LLM.

    Handles common issues:
    - Markdown code blocks (```json...```)
    - Trailing commas
    - Unescaped quotes
    - Incomplete JSON

    Args:
        response: Raw string response from LLM

    Returns:
        dict: Parsed JSON object

    Raises:
        json.JSONDecodeError: If response cannot be parsed as JSON
        ValueError: If response is empty or parsed JSON is not a dictionary
    """
    if not response or not response.strip():
        raise ValueError(
            "Cannot parse empty response. "
            "LLM returned empty or whitespace-only string."
        )

    original_length = len(response)
    response = response.strip()

    if response.startswith("```json"):
        logger.debug("Removing markdown '```json' wrapper")
        response = response[7:]
    if response.startswith("```"):
        logger.debug("Removing markdown '```' wrapper")
        response = response[3:]
    if response.endswith("```"):
        logger.debug("Removing trailing '```'")
        response = response[:-3]
    response = response.strip()

    cleaned_length = len(response)
    if original_length != cleaned_length:
        logger.debug(
            f"Cleaned response: {original_length} → {cleaned_length} chars"
        )

    try:
        logger.debug("Attempting JSON repair before parsing")
        repaired_response = repair_json(response)
        if repaired_response != response:
            logger.info(
                "JSON repair made changes to the response. "
                f"Original length: {len(response)}, "
                f"Repaired length: {len(repaired_response)}"
            )
        response = repaired_response
    except Exception as e:
        raise ValueError(
            f"JSON repair failed: {e}. " f"Response preview: {response[:200]}"
        ) from e

    try:
        parsed_json = json.loads(response)
    except json.JSONDecodeError as e:
        error_msg = (
            f"Failed to parse JSON even after repair. "
            f"Error: {e.msg} at line {e.lineno} column {e.colno}. "
            f"Response preview: {response[:200]}"
        )
        raise json.JSONDecodeError(error_msg, e.doc, e.pos) from e

    if not isinstance(parsed_json, dict):
        type_name = type(parsed_json).__name__
        raise ValueError(
            f"LLM returned {type_name} instead of dict. "
            f"Content: {str(parsed_json)[:200]}"
        )

    logger.debug(
        f"Successfully parsed JSON with {len(parsed_json)} top-level keys"
    )
    return parsed_json
