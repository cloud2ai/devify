import logging

from devtoolbox.llm.azure_openai_provider import AzureOpenAIConfig
from devtoolbox.llm.service import LLMService
from django.conf import settings

logger = logging.getLogger(__name__)


def call_llm(prompt, content=None, output_language=None):
    """
    Call LLM with optional output language specification.

    Args:
        prompt: System prompt for the LLM
        content: User content to process (optional)
        output_language: Desired output language (optional)

    Returns:
        str: LLM response (guaranteed to be a string, may be empty)

    Raises:
        ValueError: If LLM service returns None or invalid type
        Exception: If LLM service call fails
    """
    try:
        llm_config = AzureOpenAIConfig(**settings.AZURE_OPENAI_CONFIG)
        llm_service = LLMService(llm_config)

        final_prompt = prompt
        if output_language:
            final_prompt = (
                f"Your output language is {output_language}.\n\n{prompt}"
            )

        messages = [{"role": "system", "content": final_prompt}]
        if content:
            messages.append({"role": "user", "content": content})

        max_tokens = settings.AZURE_OPENAI_CONFIG.get('max_tokens', 10000)
        temperature = settings.AZURE_OPENAI_CONFIG.get('temperature', 0.3)

        logger.info(
            f"Calling LLM with {len(messages)} messages, "
            f"content length: {len(content) if content else 0} chars, "
            f"max_tokens: {max_tokens}, temperature: {temperature}"
        )

        response = llm_service.chat(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )

        if response is None:
            error_msg = "LLM service returned None response"
            logger.error(error_msg)
            raise ValueError(error_msg)

        if not isinstance(response, str):
            logger.warning(
                f"LLM service returned unexpected type: {type(response)}, "
                f"converting to string"
            )
            response = str(response)

        logger.info(
            f"LLM response received: {len(response)} chars"
        )
        return response

    except Exception as e:
        logger.error(f"LLM service call failed: {e}", exc_info=True)
        raise