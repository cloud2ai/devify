"""
AI Services configuration for LLM and OCR.

This module configures:
- Azure OpenAI for LLM text generation
- Azure Document Intelligence for OCR
- LLM output language preferences
"""

import os

# ============================
# Azure OpenAI Configuration
# ============================

# AZURE_OPENAI_CONFIG: Azure OpenAI service configuration
# - Use Case: LLM text generation for email processing and analysis
# - Security: Store API_KEY in environment variables only
# - Documentation: https://learn.microsoft.com/en-us/azure/ai-services/openai/
AZURE_OPENAI_CONFIG = {
    # API base URL from Azure OpenAI resource
    # Format: https://{your-resource-name}.openai.azure.com/
    'api_base': os.getenv('AZURE_OPENAI_API_BASE'),

    # API key for authentication
    # Security: Never commit this to version control
    # How to get: Azure Portal → OpenAI Resource → Keys and Endpoint
    'api_key': os.getenv('AZURE_OPENAI_API_KEY'),

    # Deployment name created in Azure OpenAI Studio
    # Example: 'gpt-4', 'gpt-35-turbo'
    'deployment': os.getenv('AZURE_OPENAI_DEPLOYMENT'),

    # API version for Azure OpenAI service
    # Format: YYYY-MM-DD (e.g., '2023-05-15')
    # Latest versions: https://learn.microsoft.com/en-us/azure/ai-services/openai/reference
    'api_version': os.getenv('AZURE_OPENAI_API_VERSION'),

    # Maximum tokens for LLM response
    # - Use Case: Control response length and cost
    # - Range: 1-4096 (varies by model)
    # - Default: 10000
    # - Note: Higher values increase cost and latency
    'max_tokens': int(os.getenv('AZURE_OPENAI_MAX_TOKENS', '10000')),

    # Temperature for response randomness
    # - Use Case: Control creativity vs consistency
    # - Range: 0.0-1.0
    # - Default: 0.5 (balanced)
    # - 0.0: Deterministic, consistent responses
    # - 1.0: Creative, varied responses
    'temperature': float(os.getenv('AZURE_OPENAI_TEMPERATURE', '0.5')),
}

# ============================
# Azure OCR Configuration
# ============================

# AZURE_OCR_CONFIG: Azure Document Intelligence configuration
# - Use Case: OCR for processing email attachments (PDF, images)
# - Documentation: https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/
AZURE_OCR_CONFIG = {
    # API key for Azure Document Intelligence
    # Security: Never commit this to version control
    # How to get: Azure Portal → Document Intelligence → Keys and Endpoint
    'api_key': os.getenv('AZURE_DOCUMENT_INTELLIGENCE_KEY'),

    # Endpoint URL for Azure Document Intelligence
    # Format: https://{your-resource-name}.cognitiveservices.azure.com/
    'endpoint': os.getenv('AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT'),
}

# ============================
# LLM Output Configuration
# ============================

# LLM_OUTPUT_LANGUAGE: Preferred language for LLM responses
# - Use Case: Control the language of generated summaries and content
# - Default: 'English'
# - Supported: Any language supported by the model
# - Examples: 'English', 'Chinese', 'Spanish', 'French'
# - Note: This is a preference; actual output depends on prompt
LLM_OUTPUT_LANGUAGE = os.getenv('LLM_OUTPUT_LANGUAGE', 'English')
