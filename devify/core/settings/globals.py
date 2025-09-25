"""
This file is used for defining custom global configuration settings.
It primarily handles configurations through environment variables.
For global constants, please define them in the utils module.
"""

import os

# Email attachment storage configuration
EMAIL_ATTACHMENT_STORAGE_PATH = os.getenv(
    'EMAIL_ATTACHMENT_STORAGE_PATH', '/tmp/attachments')
TMP_EMAIL_ATTACHMENT_STORAGE_PATH = os.getenv(
    'TMP_EMAIL_ATTACHMENT_STORAGE_PATH', '/tmp/tmp_attachments')

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

# Azure OCR configuration dictionary.
AZURE_OCR_CONFIG = {
    # The API key for Azure Document Intelligence
    'api_key': os.getenv('AZURE_DOCUMENT_INTELLIGENCE_KEY'),
    # The endpoint for Azure Document Intelligence
    'endpoint': os.getenv('AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT'),
}

# LLM output language configuration
LLM_OUTPUT_LANGUAGE = os.getenv('LLM_OUTPUT_LANGUAGE', 'English')

# Haraka email system configuration
AUTO_ASSIGN_EMAIL_DOMAIN = os.getenv(
    'AUTO_ASSIGN_EMAIL_DOMAIN', 'aimychats.com'
)
DEFAULT_LANGUAGE = os.getenv(
    'DEFAULT_LANGUAGE', 'en-US'
)
DEFAULT_SCENE = os.getenv(
    'DEFAULT_SCENE', 'chat'
)
THREADLINE_CONFIG_PATH = os.getenv(
    'THREADLINE_CONFIG_PATH', '/opt/devify/conf/threadline'
)

# File-based email processing configuration
EMAIL_BASE_DIR = os.getenv('EMAIL_BASE_DIR', '/opt/haraka/emails')
EMAIL_INBOX_DIR = os.getenv('EMAIL_INBOX_DIR', f'{EMAIL_BASE_DIR}/inbox')
EMAIL_PROCESSING_DIR = os.getenv('EMAIL_PROCESSING_DIR', f'{EMAIL_BASE_DIR}/processing')
EMAIL_FAILED_DIR = os.getenv('EMAIL_FAILED_DIR', f'{EMAIL_BASE_DIR}/failed')
