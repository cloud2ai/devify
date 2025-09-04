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
        str: LLM response
    """
    llm_config = AzureOpenAIConfig(**settings.AZURE_OPENAI_CONFIG)
    llm_service = LLMService(llm_config)

    # Add output language instruction to prompt if specified
    final_prompt = prompt
    if output_language:
        final_prompt = f"Your output language is {output_language}.\n\n{prompt}"

    messages = [{"role": "system", "content": final_prompt}]
    if content:
        messages.append({"role": "user", "content": content})

    logger.info(f"Calling LLM with prompt: {messages}")
    response = llm_service.chat(
        messages=messages,
        max_tokens=10000,
        temperature=0.3
    )
    logger.info(f"LLM response: {response}")
    return response