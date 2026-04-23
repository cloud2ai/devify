import logging
from typing import Any, Dict, Optional, Tuple

from agentcore_metering.adapters.django import (
    LLMTracker as AgentcoreLLMTracker,
)
from django.conf import settings
from django.utils import timezone
from threadline.utils.agentcore_bridge import ensure_default_llm_config
from threadline.utils.llm import parse_json_response

logger = logging.getLogger(__name__)


class LLMTracker:
    """
    Business-level LLM API call tracker for billing and monitoring

    This service wraps LLM API calls to automatically extract and record
    token usage information, supporting billing and cost analysis.

    This is NOT a pure technical library - it handles business logic
    like recording usage to state for billing purposes.
    """

    @staticmethod
    def call_and_track(
        prompt: str,
        content: Optional[str] = None,
        json_mode: bool = False,
        max_retries: int = 0,
        state: Optional[Dict] = None,
        node_name: str = "unknown",
        model_uuid: Optional[str] = None,
    ) -> Tuple[Any, Dict[str, Any]]:
        """
        Call LLM API with automatic usage tracking

        This method wraps LLM API calls to automatically extract and record
        token usage information from the API response, eliminating the need
        for manual token estimation.

        Args:
            prompt: System prompt for the LLM
            content: User content to process (optional)
            json_mode: If True, expect JSON response format
            max_retries: Maximum retry attempts (not implemented)
            state: EmailState dict (optional, for tracking)
            node_name: Name of the calling node (for tracking)

        Returns:
            (response_content, usage_dict)
            - response_content: LLM response text
            - usage_dict: Token usage with keys:
                - model: Model name
                - prompt_tokens: Input token count
                - completion_tokens: Output token count
                - total_tokens: Total token count
                - cached_tokens: Cached token count (optional)
                - reasoning_tokens: Reasoning token count (optional)

        Raises:
            ValueError: If prompt is empty or API returns no usage data
            Exception: If LLM API call fails

        Note:
            Token usage is extracted from API response 'usage' field.
            OpenAI API always returns usage data in successful responses.
            If usage data is missing, an error is raised.
        """
        if not prompt:
            raise ValueError("Prompt cannot be empty")

        messages = [{"role": "system", "content": prompt}]
        if content:
            messages.append({"role": "user", "content": content})

        return LLMTracker.call_messages_and_track(
            messages=messages,
            json_mode=json_mode,
            max_retries=max_retries,
            state=state,
            node_name=node_name,
            model_uuid=model_uuid,
        )

    @staticmethod
    def call_messages_and_track(
        messages: list,
        json_mode: bool = False,
        max_retries: int = 0,
        state: Optional[Dict] = None,
        node_name: str = "unknown",
        model_uuid: Optional[str] = None,
    ) -> Tuple[Any, Dict[str, Any]]:
        """
        Call LLM API with prebuilt messages and automatic usage tracking.

        This variant is used for multimodal inputs where the user message
        needs to contain both text and image blocks.
        """
        if not messages:
            raise ValueError("Messages cannot be empty")

        try:
            ensure_default_llm_config()

            response_content, usage = AgentcoreLLMTracker.call_and_track(
                messages=messages,
                json_mode=json_mode,
                node_name=node_name,
                state=state,
                model_uuid=model_uuid,
                json_attempts=max(1, int(max_retries) + 1),
            )

            if json_mode and isinstance(response_content, str):
                try:
                    response_content = parse_json_response(response_content)
                    logger.debug(f"Parsed JSON response in {node_name}")
                except Exception as e:
                    logger.warning(
                        "Failed to parse JSON response in %s: %s. "
                        "Returning raw string.",
                        node_name,
                        e,
                    )

            if state is not None and settings.ENABLE_COST_TRACKING:
                tracking_data = {
                    "node": node_name,
                    "model": usage["model"],
                    "input_tokens": usage["prompt_tokens"],
                    "output_tokens": usage["completion_tokens"],
                    "total_tokens": usage["total_tokens"],
                    "cached_tokens": usage.get("cached_tokens", 0),
                    "reasoning_tokens": usage.get("reasoning_tokens", 0),
                    "success": True,
                    "error": None,
                    "timestamp": timezone.now().isoformat(),
                }
                state.setdefault("llm_calls", []).append(tracking_data)

            logger.info(
                "LLM call succeeded in %s: %s tokens "
                "(prompt=%s, completion=%s)",
                node_name,
                usage["total_tokens"],
                usage["prompt_tokens"],
                usage["completion_tokens"],
            )

            return response_content, usage

        except Exception as e:
            logger.error("LLM call failed in %s: %s", node_name, e)

            model = str(model_uuid) if model_uuid else "unknown"
            if state is not None and settings.ENABLE_COST_TRACKING:
                state.setdefault("llm_calls", []).append(
                    {
                        "node": node_name,
                        "model": model,
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "total_tokens": 0,
                        "success": False,
                        "error": str(e),
                        "timestamp": timezone.now().isoformat(),
                    }
                )

            raise
