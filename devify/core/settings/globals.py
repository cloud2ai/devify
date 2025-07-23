"""
This file is used for defining custom global configuration settings.
It primarily handles configurations through environment variables.
For global constants, please define them in the utils module.
"""

import os

# Email attachment storage configuration
EMAIL_ATTACHMENT_STORAGE_PATH = os.getenv(
    'EMAIL_ATTACHMENT_STORAGE_PATH', '/tmp/attachments')

# Azure OpenAI configuration
AZURE_OPENAI_CONFIG = {
    # The API base URL
    'api_base': os.getenv('AZURE_OPENAI_API_BASE'),
    # The API key
    'api_key': os.getenv('AZURE_OPENAI_API_KEY'),
    # The deployment name
    'deployment': os.getenv('AZURE_OPENAI_DEPLOYMENT'),
    # The API version
    'api_version': os.getenv('AZURE_OPENAI_API_VERSION'),
    # The max tokens for response
    'max_tokens': int(os.getenv('AZURE_OPENAI_MAX_TOKENS', '10000')),
    # The temperature for response randomness
    'temperature': float(os.getenv('AZURE_OPENAI_TEMPERATURE', '0.5')),
}

"""
Azure OCR configuration dictionary.
"""

AZURE_OCR_CONFIG = {
    # The API key for Azure Document Intelligence
    'api_key': os.getenv('AZURE_DOCUMENT_INTELLIGENCE_KEY'),
    # The endpoint for Azure Document Intelligence
    'endpoint': os.getenv('AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT'),
}
