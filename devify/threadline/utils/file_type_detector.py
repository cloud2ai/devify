"""
File Type Detection Utilities

This module provides utilities for detecting file types using
python-magic (libmagic). It offers a clean interface for file type
detection that can be used across the application.
"""

import logging
from typing import Dict, List, Optional, Tuple

import magic

logger = logging.getLogger(__name__)

# File type extension mapping for MIME types
CONTENT_TYPE_EXTENSION_MAP = {
    # Images
    'jpeg': '.jpg',
    'jpg': '.jpg',
    'png': '.png',
    'gif': '.gif',
    'webp': '.webp',
    'bmp': '.bmp',
    'tiff': '.tiff',
    'svg': '.svg',
    'image/jpeg': '.jpg',
    'image/jpg': '.jpg',
    'image/png': '.png',
    'image/gif': '.gif',
    'image/webp': '.webp',
    'image/bmp': '.bmp',
    'image/tiff': '.tiff',
    'image/svg+xml': '.svg',
    'image/x-icon': '.ico',
    # Documents
    'text/plain': '.txt',
    'text/html': '.html',
    'text/css': '.css',
    'text/javascript': '.js',
    'application/json': '.json',
    'application/xml': '.xml',
    'application/pdf': '.pdf',
    'application/rtf': '.rtf',
    # Microsoft Office
    'application/msword': '.doc',
    'application/vnd.openxmlformats-officedocument.'
    'wordprocessingml.document': (
        '.docx'
    ),
    'application/vnd.ms-excel': '.xls',
    'application/vnd.openxmlformats-officedocument.'
    'spreadsheetml.sheet': (
        '.xlsx'
    ),
    'application/vnd.ms-powerpoint': '.ppt',
    'application/vnd.openxmlformats-officedocument.'
    'presentationml.presentation': (
        '.pptx'
    ),
    # Archives
    'application/zip': '.zip',
    'application/x-rar-compressed': '.rar',
    'application/x-tar': '.tar',
    'application/gzip': '.gz',
    'application/x-7z-compressed': '.7z',
    # Audio
    'audio/mpeg': '.mp3',
    'audio/wav': '.wav',
    'audio/ogg': '.ogg',
    'audio/flac': '.flac',
    # Video
    'video/mp4': '.mp4',
    'video/avi': '.avi',
    'video/quicktime': '.mov',
    'video/x-msvideo': '.avi',
    # Other
    'application/octet-stream': '.bin'
}


class FileTypeDetector:
    """
    File type detector using python-magic (libmagic).

    This class provides a clean interface for detecting file types from
    file content. It uses the same underlying library as the Linux 'file'
    command.
    """

    def __init__(self):
        """Initialize the file type detector."""
        self._mime_detector = magic.Magic(mime=True)
        self._description_detector = magic.Magic()
        logger.debug("FileTypeDetector initialized successfully")

    def detect_file_type(self, payload) -> Tuple[str, str, str]:
        """
        Detect file type from payload.

        Args:
            payload: File content as bytes or string

        Returns:
            Tuple[str, str, str]: (mime_type, extension, description)
        """
        if not payload:
            return 'application/octet-stream', '', 'Empty file'

        # Convert string to bytes for detection if needed
        if isinstance(payload, str):
            payload_bytes = payload.encode('utf-8')
        else:
            payload_bytes = payload

        # Detect MIME type using python-magic
        mime_type = self._mime_detector.from_buffer(payload_bytes)

        # Get detailed file description
        description = self._description_detector.from_buffer(
            payload_bytes
        )

        # Get file extension from MIME type
        extension = get_extension_from_mime_type(mime_type)

        logger.debug(f"Detected: {mime_type} -> {extension}")
        return mime_type, extension, description

    def is_image_file(
        self, payload, content_type: str = '', filename: str = ''
    ) -> bool:
        """
        Check if a file is an image based on content and metadata.

        Args:
            payload: File content as bytes or string
            content_type: MIME content type (optional)
            filename: Original filename (optional)

        Returns:
            bool: True if file is detected as an image
        """
        if not payload:
            return False

        # Try detection from file content first
        mime_type, _, _ = self.detect_file_type(payload)
        if mime_type.startswith('image/'):
            return True

        # Fall back to content type if content detection fails
        if content_type and content_type.startswith('image/'):
            return True

        return False


def get_extension_from_mime_type(mime_type: str) -> str:
    """
    Get file extension from MIME type.

    Args:
        mime_type: MIME type string

    Returns:
        str: File extension with leading dot
    """
    return CONTENT_TYPE_EXTENSION_MAP.get(mime_type, '')

def get_supported_file_types() -> Dict[str, List[str]]:
    """
    Get information about supported file types for detection.

    Returns:
        Dict containing categorized supported file types
    """
    categories = {
        'images': [],
        'documents': [],
        'archives': [],
        'audio': [],
        'video': [],
        'other': []
    }

    # Categorize file types based on MIME type and extension
    for mime_type, ext in CONTENT_TYPE_EXTENSION_MAP.items():
        # Check for image files
        image_extensions = [
            '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff',
            '.svg', '.ico'
        ]
        if mime_type.startswith('image/') or ext in image_extensions:
            categories['images'].append(f"{mime_type} ({ext})")
        # Check for document files
        elif mime_type.startswith('text/'):
            categories['documents'].append(f"{mime_type} ({ext})")
        elif (mime_type.startswith('application/') and
              'office' in mime_type):
            categories['documents'].append(f"{mime_type} ({ext})")
        elif ext in ['.pdf', '.doc', '.docx', '.txt', '.html']:
            categories['documents'].append(f"{mime_type} ({ext})")
        # Check for archive files
        elif ('zip' in mime_type or 'rar' in mime_type or
              'tar' in mime_type or '7z' in mime_type):
            categories['archives'].append(f"{mime_type} ({ext})")
        elif ext in ['.zip', '.rar', '.tar', '.gz', '.7z']:
            categories['archives'].append(f"{mime_type} ({ext})")
        # Check for audio files
        elif mime_type.startswith('audio/'):
            categories['audio'].append(f"{mime_type} ({ext})")
        elif ext in ['.mp3', '.wav', '.ogg', '.flac']:
            categories['audio'].append(f"{mime_type} ({ext})")
        # Check for video files
        elif mime_type.startswith('video/'):
            categories['video'].append(f"{mime_type} ({ext})")
        elif ext in ['.mp4', '.avi', '.mov']:
            categories['video'].append(f"{mime_type} ({ext})")
        # All other file types
        else:
            categories['other'].append(f"{mime_type} ({ext})")

    return categories
