"""
Email utilities package

This package contains all email-related utilities and tools for the
threadline application. Organized into subpackages for better structure
and maintainability.

Subpackages:
- config: Email configuration management
- parsers: Email parsing utilities (enhanced, legacy, image)
- clients: Email client implementations (IMAP)
- processor: Email processing orchestration
- service: Email save and storage services
"""

from .clients.imap import IMAPClient
from .config import EmailConfigManager, EmailSource
from .parsers.enhanced import EmailFlankerParser
from .parsers.image import (
    EmailImageProcessor,
    HTML_IMG_PATTERNS,
    process_email_images,
)
from .parsers.legacy import EmailParser
from .processor import EmailProcessor, ParserType
from .service import EmailSaveService

__all__ = [
    'EmailConfigManager',
    'EmailFlankerParser',
    'EmailImageProcessor',
    'EmailParser',
    'EmailProcessor',
    'EmailSaveService',
    'EmailSource',
    'HTML_IMG_PATTERNS',
    'IMAPClient',
    'ParserType',
    'process_email_images',
]
