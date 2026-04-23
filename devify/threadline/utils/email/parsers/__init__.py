"""
Email parsers package

Contains various email parsing utilities and implementations.

Parsers:
- enhanced: Advanced parser using flanker library
- legacy: Original parser (deprecated)
- image: Image processing utilities
"""

from typing import TYPE_CHECKING

from .image import (
    EmailImageProcessor,
    HTML_IMG_PATTERNS,
    process_email_images,
)
from .legacy import EmailParser

if TYPE_CHECKING:
    from .enhanced import EmailFlankerParser as _EmailFlankerParser


def __getattr__(name: str):
    if name == "EmailFlankerParser":
        from .enhanced import EmailFlankerParser

        return EmailFlankerParser
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "EmailFlankerParser",
    "EmailImageProcessor",
    "EmailParser",
    "HTML_IMG_PATTERNS",
    "process_email_images",
]
