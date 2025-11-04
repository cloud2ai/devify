import logging
from typing import Any, Dict, Optional, Tuple

from django.conf import settings
from django.utils import timezone

from devtoolbox.llm.azure_openai_provider import AzureOpenAIConfig
from devtoolbox.llm.service import LLMService

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
        node_name: str = 'unknown'
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

        llm_config = AzureOpenAIConfig(**settings.AZURE_OPENAI_CONFIG)
        llm_service = LLMService(llm_config)

        messages = [{"role": "system", "content": prompt}]
        if content:
            messages.append({"role": "user", "content": content})

        max_tokens = settings.AZURE_OPENAI_CONFIG['max_tokens']
        temperature = settings.AZURE_OPENAI_CONFIG['temperature']
        model = settings.AZURE_OPENAI_CONFIG.get('model', 'gpt-4')

        chat_kwargs = {
            'messages': messages,
            'max_tokens': max_tokens,
            'temperature': temperature
        }

        if json_mode:
            try:
                chat_kwargs['response_format'] = {"type": "json_object"}
            except TypeError:
                pass

        chat_kwargs['raw_response'] = True

        try:
            response_obj = llm_service.chat(**chat_kwargs)

            if response_obj is None:
                raise ValueError("LLM service returned None response")

            response_content = None
            usage = None

            actual_model = model
            if hasattr(response_obj, 'response_metadata'):
                actual_model = response_obj.response_metadata.get(
                    'model_name', model
                )

            if hasattr(response_obj, 'content'):
                response_content = response_obj.content

                if hasattr(response_obj, 'usage_metadata'):
                    usage_meta = response_obj.usage_metadata
                    input_tokens = usage_meta.get('input_tokens', 0)
                    output_tokens = usage_meta.get('output_tokens', 0)
                    total_tokens = usage_meta.get('total_tokens', 0)

                    usage = {
                        'model': actual_model,
                        'prompt_tokens': input_tokens,
                        'completion_tokens': output_tokens,
                        'total_tokens': total_tokens,
                    }

                    if 'input_token_details' in usage_meta:
                        details = usage_meta['input_token_details']
                        usage['cached_tokens'] = details.get(
                            'cache_read', 0
                        )

                    if 'output_token_details' in usage_meta:
                        details = usage_meta['output_token_details']
                        reasoning = details.get('reasoning', 0)
                        usage['reasoning_tokens'] = reasoning
            else:
                response_content = str(response_obj)

            if not usage:
                error_msg = (
                    f"Unable to extract usage from API response "
                    f"in {node_name}. "
                    f"This should not happen with OpenAI API."
                )
                logger.error(error_msg)
                raise ValueError(error_msg)

            if state is not None and settings.ENABLE_COST_TRACKING:
                tracking_data = {
                    'node': node_name,
                    'model': usage['model'],
                    'input_tokens': usage['prompt_tokens'],
                    'output_tokens': usage['completion_tokens'],
                    'total_tokens': usage['total_tokens'],
                    'cached_tokens': usage.get('cached_tokens', 0),
                    'reasoning_tokens': usage.get('reasoning_tokens', 0),
                    'success': True,
                    'error': None,
                    'timestamp': timezone.now().isoformat()
                }
                state.setdefault('llm_calls', []).append(tracking_data)

            logger.info(
                f"LLM call succeeded in {node_name}: "
                f"{usage['total_tokens']} tokens "
                f"(prompt={usage['prompt_tokens']}, "
                f"completion={usage['completion_tokens']})"
            )

            return response_content, usage

        except Exception as e:
            logger.error(f"LLM call failed in {node_name}: {e}")

            if state is not None and settings.ENABLE_COST_TRACKING:
                state.setdefault('llm_calls', []).append({
                    'node': node_name,
                    'model': model,
                    'input_tokens': 0,
                    'output_tokens': 0,
                    'total_tokens': 0,
                    'success': False,
                    'error': str(e),
                    'timestamp': timezone.now().isoformat()
                })

            raise
