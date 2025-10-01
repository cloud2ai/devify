"""
Email parsers package

Contains various email parsing utilities and implementations.

Parsers:
- enhanced: Advanced parser using flanker library
- legacy: Original parser (deprecated)
- image: Image processing utilities
"""

from .enhanced import EmailFlankerParser
from .image import (
    EmailImageProcessor,
    HTML_IMG_PATTERNS,
    process_email_images,
)
from .legacy import EmailParser

__all__ = [
    'EmailFlankerParser',
    'EmailImageProcessor',
    'EmailParser',
    'HTML_IMG_PATTERNS',
    'process_email_images',
]
