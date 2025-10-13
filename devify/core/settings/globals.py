"""
This file is used for defining custom global configuration settings.
It primarily handles configurations through environment variables.
For global constants, please define them in the utils module.
"""

import os

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
    'AUTO_ASSIGN_EMAIL_DOMAIN', 'devify.local'
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

# Haraka email system configuration
HARAKA_EMAIL_BASE_DIR = os.getenv(
    'HARAKA_EMAIL_BASE_DIR', '/opt/haraka/emails'
)

# Email attachment storage configuration
EMAIL_ATTACHMENT_DIR = os.getenv(
    'EMAIL_ATTACHMENT_DIR', '/opt/email_attachments')
TMP_EMAIL_ATTACHMENT_DIR = '/tmp/email_attachments'


# Task Timeout Configuration
TASK_TIMEOUT_MINUTES = os.getenv('TASK_TIMEOUT_MINUTES', 10)

# Email Cleanup Configuration
EMAIL_CLEANUP_CONFIG = {
    # Inbox directory timeout in hours
    'inbox_timeout_hours': int(
        os.getenv('EMAIL_CLEANUP_INBOX_TIMEOUT_HOURS', '1')
    ),
    # Processed directory timeout in minutes
    'processed_timeout_minutes': int(
        os.getenv('EMAIL_CLEANUP_PROCESSED_TIMEOUT_MINUTES', '10')
    ),
    # Failed directory timeout in minutes
    'failed_timeout_minutes': int(
        os.getenv('EMAIL_CLEANUP_FAILED_TIMEOUT_MINUTES', '10')
    ),
    # EmailTask retention period in days
    'email_task_retention_days': int(
        os.getenv('EMAIL_CLEANUP_TASK_RETENTION_DAYS', '3')
    ),
}