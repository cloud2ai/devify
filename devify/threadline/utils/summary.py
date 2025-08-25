import logging

from devtoolbox.llm.azure_openai_provider import AzureOpenAIConfig
from devtoolbox.llm.service import LLMService
from django.conf import settings

logger = logging.getLogger(__name__)


def call_llm(prompt, content=None):
    llm_config = AzureOpenAIConfig(**settings.AZURE_OPENAI_CONFIG)
    llm_service = LLMService(llm_config)

    messages = [{"role": "system", "content": prompt}]
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