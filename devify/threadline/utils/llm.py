import json
import logging
from typing import Any, Dict, Optional

import litellm
from json_repair import repair_json

from agentcore_metering.adapters.django.services.runtime_config import (
    get_litellm_params,
)

logger = logging.getLogger(__name__)


def _extract_llm_content(response: Any) -> str:
    choices = getattr(response, "choices", None) or []
    if not choices:
        raise ValueError("LLM response did not include any choices")

    first_choice = choices[0]
    message = getattr(first_choice, "message", None) or {}
    content = getattr(message, "content", None)
    if content is None and isinstance(message, dict):
        content = message.get("content")

    if content is None:
        content = getattr(first_choice, "delta", None)
        if content is not None and hasattr(content, "content"):
            content = content.content

    if content is None:
        raise ValueError("LLM response did not include message content")

    return str(content)


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


def call_llm(
    prompt: str,
    content: Optional[str] = None,
    json_mode: bool = False,
    max_retries: int = 0,
):
    """
    Call LLM with optional JSON response format and retry logic.

    Args:
        prompt: System prompt for the LLM
        content: User content to process (optional)
        json_mode: If True, expect JSON response and return parsed dict.
                   If False, return raw string response.
        max_retries: Maximum number of retry attempts for JSON parsing
                     (only used when json_mode=True, default: 0)

    Returns:
        dict: Parsed JSON response (if json_mode=True)
        str: Raw string response (if json_mode=False)

    Raises:
        ValueError: If json_mode=True and all retries fail to produce
                    valid JSON, or if LLM service returns no response
        Exception: If LLM service call fails for other reasons
    """
    if not prompt:
        raise ValueError("Prompt cannot be empty")

    params = get_litellm_params()
    messages = [{"role": "system", "content": prompt}]
    if content:
        messages.append({"role": "user", "content": content})

    params["messages"] = messages
    if json_mode:
        params["response_format"] = {"type": "json_object"}

    max_attempts = max_retries + 1 if json_mode else 1
    last_error = None

    logger.info(
        f"Initializing LLM call - "
        f"json_mode: {json_mode}, "
        f"max_retries: {max_retries}, "
        f"model: {params.get('model')}, "
        f"max_tokens: {params.get('max_tokens')}, "
        f"temperature: {params.get('temperature')}"
    )

    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(
                f"Attempt {attempt}/{max_attempts}: "
                f"Sending {len(messages)} message(s) to LLM "
                f"(prompt: {len(prompt)} chars, "
                f"content: {len(content) if content else 0} chars)"
            )

            response = litellm.completion(**params)
            if response is None:
                raise ValueError("LLM service returned None response")

            response_content = _extract_llm_content(response)

            logger.info(
                f"Attempt {attempt}/{max_attempts}: "
                f"Received response with {len(response_content)} chars"
            )

            if not json_mode:
                logger.info("Returning raw string response (json_mode=False)")
                return response_content

            parsed_json = parse_json_response(response_content)
            logger.info(
                f"Attempt {attempt}/{max_attempts}: "
                f"Successfully parsed JSON with {len(parsed_json)} keys"
            )
            return parsed_json

        except (json.JSONDecodeError, ValueError) as e:
            error_type = type(e).__name__
            logger.warning(
                f"Attempt {attempt}/{max_attempts} failed: "
                f"{error_type}: {str(e)}"
            )
            if last_error is None:
                last_error = e
            if attempt < max_attempts:
                logger.info(
                    f"Retrying LLM call... "
                    f"(next attempt: {attempt + 1}/{max_attempts})"
                )
                continue

        except Exception as e:
            exc_type = type(e).__name__
            logger.error(
                f"Attempt {attempt}/{max_attempts} failed "
                f"with unexpected error: {exc_type}: {str(e)}",
                exc_info=True,
            )
            last_error = e
            if attempt < max_attempts:
                logger.info(
                    f"Retrying after unexpected error... "
                    f"(next attempt: {attempt + 1}/{max_attempts})"
                )
                continue
            raise

    last_error_type = type(last_error).__name__
    last_error_msg = str(last_error)
    error_msg = (
        f"Failed to get valid JSON response after "
        f"{max_attempts} attempt(s). "
        f"Last error: {last_error_type}: {last_error_msg}"
    )
    logger.error(
        f"{error_msg}. "
        f"Consider checking: prompt format, response_format support, "
        f"or increasing max_retries."
    )
    raise ValueError(error_msg) from last_error
