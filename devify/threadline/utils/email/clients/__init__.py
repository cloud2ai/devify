"""
Email clients package

Contains email client implementations for different protocols.
"""

from .imap import IMAPClient

__all__ = [
    'IMAPClient',
]
