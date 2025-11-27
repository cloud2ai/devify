"""
Email system configuration for Haraka integration and email processing.

This module configures:
- Haraka email server integration
- Email attachment storage and handling
- Email cleanup and retention policies
- Auto-assignment and default settings
"""

import os

# ============================
# Email Auto-Assignment Configuration
# ============================

# AUTO_ASSIGN_EMAIL_DOMAIN: Default domain for auto-assigned email addresses
# - Use Case: Automatically assign email addresses to users
# - Format: domain.com (without @)
# - Default: 'devify.local'
# - Example: User 'john' gets 'john@devify.local'
AUTO_ASSIGN_EMAIL_DOMAIN = os.getenv(
    'AUTO_ASSIGN_EMAIL_DOMAIN', 'devify.local'
)

# ============================
# Default User Preferences
# ============================

# DEFAULT_LANGUAGE: Default language for new users
# - Use Case: Initial language preference for UI and content
# - Format: ISO 639-1 language code with optional region
# - Default: 'en-US'
# - Examples: 'en-US', 'zh-CN', 'es-ES', 'fr-FR'
DEFAULT_LANGUAGE = os.getenv('DEFAULT_LANGUAGE', 'en-US')

# DEFAULT_SCENE: Default scene/context for email processing
# - Use Case: Initial context mode for new users
# - Default: 'chat'
# - Examples: 'chat', 'business', 'support'
# - Note: Affects LLM prompt templates and processing behavior
DEFAULT_SCENE = os.getenv('DEFAULT_SCENE', 'chat')

# ============================
# Threadline Configuration
# ============================

# THREADLINE_CONFIG_PATH: Path to Threadline configuration files
# - Use Case: Store user-specific email processing configurations
# - Default: '/opt/devify/conf/threadline'
# - Security: Ensure proper file permissions (readable by Django)
# - Note: Used for storing scene templates and processing rules
THREADLINE_CONFIG_PATH = os.getenv(
    'THREADLINE_CONFIG_PATH', '/opt/devify/conf/threadline'
)

# ============================
# Haraka Email Server Integration
# ============================

# HARAKA_EMAIL_BASE_DIR: Base directory for Haraka email storage
# - Use Case: Root directory where Haraka stores received emails
# - Default: '/opt/haraka/emails'
# - Structure: {base_dir}/{inbox|processed|failed}/
# - Security: Ensure Django has read permissions
# - Note: Haraka should be configured to write to this directory
HARAKA_EMAIL_BASE_DIR = os.getenv(
    'HARAKA_EMAIL_BASE_DIR', '/opt/haraka/emails'
)

# ============================
# Email Attachment Storage
# ============================

# EMAIL_ATTACHMENT_DIR: Permanent storage for processed email attachments
# - Use Case: Long-term storage for attachments after processing
# - Default: '/opt/email_attachments'
# - Security: Ensure proper permissions and backup strategy
# - Note: Should be on persistent storage (not ephemeral)
EMAIL_ATTACHMENT_DIR = os.getenv(
    'EMAIL_ATTACHMENT_DIR', '/opt/email_attachments'
)

# TMP_EMAIL_ATTACHMENT_DIR: Temporary storage for in-flight attachments
# - Use Case: Temporary storage during email processing
# - Default: '/tmp/email_attachments'
# - Note: Files are cleaned up after processing
# - Performance: Use fast storage (e.g., tmpfs) for better I/O
TMP_EMAIL_ATTACHMENT_DIR = '/tmp/email_attachments'

# ATTACHMENT_BASE_URL: Base URL for serving email attachments
# - Use Case: Generate URLs for attachment downloads
# - Format: https://domain.com/attachments (without trailing slash)
# - Default: '' (empty, must be configured for production)
# - Example: 'https://api.devify.com/attachments'
# - Security: Should be served through CDN or authenticated endpoint
ATTACHMENT_BASE_URL = os.getenv('ATTACHMENT_BASE_URL', '')

# ============================
# Task Timeout Configuration
# ============================

# TASK_TIMEOUT_MINUTES: Maximum execution time for email processing tasks
# - Use Case: Prevent runaway tasks from consuming resources
# - Unit: Minutes
# - Default: 10 minutes
# - Recommendation: Set based on average email processing time
# - Note: Tasks exceeding this limit will be terminated
TASK_TIMEOUT_MINUTES = int(os.getenv('TASK_TIMEOUT_MINUTES', '10'))

# ============================
# Email Cleanup and Retention Policy
# ============================

# EMAIL_CLEANUP_CONFIG: Configuration for automatic email cleanup
# - Use Case: Prevent disk space issues by cleaning old emails
# - Note: Runs as scheduled task (Celery beat)
EMAIL_CLEANUP_CONFIG = {
    # Inbox directory timeout in hours
    # - Use Case: How long to keep unprocessed emails in inbox
    # - Default: 1 hour
    # - Recommendation: Short timeout for inbox to detect stale emails
    # - Action: Emails older than this are moved to failed directory
    'inbox_timeout_hours': int(
        os.getenv('EMAIL_CLEANUP_INBOX_TIMEOUT_HOURS', '1')
    ),

    # Processed directory timeout in minutes
    # - Use Case: How long to keep successfully processed emails
    # - Default: 10 minutes
    # - Recommendation: Short timeout since data is in database
    # - Action: Emails older than this are deleted from filesystem
    'processed_timeout_minutes': int(
        os.getenv('EMAIL_CLEANUP_PROCESSED_TIMEOUT_MINUTES', '10')
    ),

    # Failed directory timeout in minutes
    # - Use Case: How long to keep failed email files for debugging
    # - Default: 10 minutes
    # - Recommendation: Increase for debugging, decrease for production
    # - Action: Failed emails older than this are deleted
    'failed_timeout_minutes': int(
        os.getenv('EMAIL_CLEANUP_FAILED_TIMEOUT_MINUTES', '10')
    ),

    # EmailTask retention period in days
    # - Use Case: How long to keep EmailTask records in database
    # - Default: 3 days
    # - Recommendation: Balance between debugging needs and database size
    # - Action: EmailTask records older than this are deleted from DB
    # - Note: Associated EmailMessage records are not affected
    'email_task_retention_days': int(
        os.getenv('EMAIL_CLEANUP_TASK_RETENTION_DAYS', '3')
    ),
}

# ============================
# Share Link Cleanup Settings
# ============================

# SHARE_LINK_CLEANUP_CONFIG: Cleanup behavior for expired share links
# - grace_period_minutes: Minutes to keep expired links active before cleanup
# - batch_size: Number of records to deactivate per iteration
SHARE_LINK_CLEANUP_CONFIG = {
    'grace_period_minutes': int(
        os.getenv('SHARE_LINK_CLEANUP_GRACE_MINUTES', '0')
    ),
    'batch_size': int(
        os.getenv('SHARE_LINK_CLEANUP_BATCH_SIZE', '500')
    )
}
