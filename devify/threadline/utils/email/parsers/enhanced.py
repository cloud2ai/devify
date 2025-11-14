"""
Enhanced Email Parser using Flanker Library

This module provides an improved email parser using the flanker library while
maintaining compatibility with the existing EmailParser interface.

File: devify/threadline/utils/email/parsers/enhanced.py

Email Parsing Flow:
1. Parse raw email data using flanker.mime.from_string()
2. Extract and decode email headers (Subject, From, To, Date)
3. Process email content:
   - Extract text and HTML parts from multipart message
   - Handle inline images and attachments
   - Position images in text content using HTML structure
4. Generate stable message ID using key email fields
5. Process and save attachments to disk
6. Return structured email data dictionary

Key Features:
- Superior multipart handling via flanker library
- Intelligent image positioning in text content
- Advanced file type detection using python-magic (libmagic)
- Safe attachment storage with MD5-based naming
- Comprehensive error handling and logging
- Full compatibility with existing EmailParser interface
"""

import hashlib
import html
import logging
import os
import re
from email.header import decode_header
from email.utils import parsedate_to_datetime
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

from bs4 import BeautifulSoup
from django.utils import timezone
from email_validator import EmailNotValidError, validate_email
from flanker import mime
from PIL import Image, UnidentifiedImageError

from .image import EmailImageProcessor
from ...file_type_detector import (
    FileTypeDetector,
    get_supported_file_types,
)

logger = logging.getLogger(__name__)


class EmailFlankerParser:
    """
    Enhanced email parser using flanker library.
    Maintains compatibility with existing EmailParser interface.
    """

    EMAIL_ATTACHMENT_PREFIX = "email_attachment_"
    IMAGE_CONTENT_TYPE_PREFIX = "image/"
    MESSAGE_ID_HASH_LENGTH = 16

    # Minimum file size for image attachments (in bytes)
    # Small images like emojis or icons are typically less than 10KB
    # This helps filter out decorative images that don't contain useful content
    # Default: 10KB (10 * 1024 bytes)
    MIN_IMAGE_ATTACHMENT_SIZE = 10 * 1024

    # Minimum image dimensions (width and height in pixels)
    # Very small images like emojis or icons are typically less than 50x50
    # This helps filter out decorative images that don't contain useful content
    # Aligned with Azure OCR minimum requirements (50x50 pixels)
    # Default: 50x50 pixels
    MIN_IMAGE_WIDTH = 50
    MIN_IMAGE_HEIGHT = 50

    # Maximum aspect ratio for image attachments
    # Images with extreme aspect ratios (like dividers, banners) are typically
    # decorative and don't contain useful content
    # Examples: 1x600 divider, 16x120 banner
    # Default: 10 (width/height or height/width)
    MAX_IMAGE_ASPECT_RATIO = 10

    def __init__(self, attachment_dir: str = "/tmp/email_attachments"):
        """
        Initialize email parser using flanker.

        Args:
            attachment_dir: Directory for storing email attachments
        """
        self.attachment_dir = attachment_dir
        self.file_detector = FileTypeDetector()
        self.image_processor = EmailImageProcessor()

    @classmethod
    def get_supported_file_types(cls) -> Dict[str, List[str]]:
        """
        Get information about supported file types for detection.

        Returns:
            Dict containing categorized supported file types
        """
        return get_supported_file_types()

    def parse_from_bytes(self, email_data: bytes) -> Optional[Dict]:
        """
        Parse email from raw bytes data using flanker.

        Args:
            email_data: Raw email data as bytes

        Returns:
            Parsed email data dictionary or None if parsing fails
        """
        # Validate input
        if not email_data:
            logger.error("Empty email data provided")
            return None

        try:
            # Parse email using mime library
            message = mime.from_string(email_data)

            if not message:
                logger.error("Failed to parse email with mime library")
                return None

            # Extract and decode email headers
            # Decode and extract email headers with line length control
            subject = self._decode_header(
                str(message.headers.get("Subject", ""))
            )
            sender = self._decode_header(
                str(message.headers.get("From", ""))
            )
            recipients = self._decode_header(
                str(message.headers.get("To", ""))
            )
            date_str = str(
                message.headers.get("Date", "")
            )

            # Parse and normalize email date
            try:
                if date_str:
                    received_at = parsedate_to_datetime(date_str)
                    if timezone.is_naive(received_at):
                        received_at = timezone.make_aware(received_at)
                else:
                    received_at = timezone.now()
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse email date '{date_str}': {e}")
                received_at = timezone.now()

            # Extract text and HTML content from message
            text_content, html_content = self._extract_content(message)

            # Generate stable unique message ID
            stable_message_id = self._generate_message_id(
                subject, sender, recipients, received_at
            )

            # Process and save email attachments
            attachments = self._process_attachments(message)

            # Clean invalid image placeholders from text content
            # (images that were filtered out during processing)
            text_content = self._clean_invalid_image_placeholders(
                text_content, attachments
            )

            return {
                "message_id": stable_message_id,
                "subject": subject,
                "sender": sender,
                "recipients": recipients,
                "received_at": received_at,
                "raw_content": email_data.decode("utf-8", errors="ignore"),
                "html_content": html_content,
                "text_content": text_content,
                "content": text_content or html_content or "",
                "attachments": attachments
            }

        except Exception as e:
            logger.error(f"Failed to parse email with mime library: {e}")
            return None

    def parse_from_file(self, file_path: str) -> Optional[Dict]:
        """
        Parse email from file using mime library.

        Args:
            file_path: Path to email file

        Returns:
            Parsed email data dictionary or None if parsing fails
        """
        try:
            with open(file_path, "rb") as f:
                email_data = f.read()
            return self.parse_from_bytes(email_data)
        except Exception as e:
            logger.error(f"Failed to parse email from file {file_path}: {e}")
            return None

    def parse_from_string(self, raw_content: str) -> Optional[Dict]:
        """
        Parse email from string content using mime library.

        Args:
            raw_content: Raw email content as string

        Returns:
            Parsed email data dictionary or None if parsing fails
        """
        try:
            email_data = raw_content.encode("utf-8")
            return self.parse_from_bytes(email_data)
        except Exception as e:
            logger.error(f"Failed to parse email from string: {e}")
            return None

    def validate_email_address(self, email_address: str) -> bool:
        """
        Validate email address using email-validator.
        """
        try:
            validate_email(email_address)
            return True
        except EmailNotValidError:
            return False

    def _generate_message_id(
        self,
        subject: str,
        sender: str,
        recipients: str,
        received_at
    ) -> str:
        """
        Generate a stable unique message_id using key email fields.
        """
        # Compose the base string for hashing
        base = (
            f"{subject}|{sender}|{recipients}|"
            f"{received_at.isoformat()}"
        )
        # Generate a hash and truncate to the required length
        msg_hash = hashlib.sha256(
            base.encode("utf-8")
        ).hexdigest()[:self.MESSAGE_ID_HASH_LENGTH]
        return f"email_{msg_hash}"

    def _detect_file_type(self, payload, content_type: str = "",
                         filename: str = "") -> Tuple[str, str]:
        """
        File type detection using file signature analysis only.

        We trust the file detection library (python-magic) completely as it
        analyzes the actual file content, which is more reliable than MIME
        types or filenames that can be easily manipulated or incorrectly set.

        Args:
            payload: File content as bytes or string
            content_type: MIME content type from email (ignored)
            filename: Original filename (ignored)

        Returns:
            Tuple[str, str]: (detected_mime_type, file_extension)
        """
        # Use file signature detection exclusively
        mime_type, extension, _ = self.file_detector.detect_file_type(payload)

        logger.debug(f"File signature detection: {mime_type} -> {extension}")
        return mime_type, extension


    def _is_image_file(self, payload, content_type: str, filename: str) -> bool:
        """
        Detect if a file is an image using the centralized FileTypeDetector.

        Args:
            payload: File content as bytes or string
            content_type: MIME content type from email
            filename: Original filename

        Returns:
            bool: True if file is detected as an image
        """
        return self.file_detector.is_image_file(payload, content_type, filename)

    def _decode_header(self, header_value: str) -> str:
        """
        Decode email header value that may be encoded in various formats.

        Handles:
        - Quoted-Printable encoding: =?utf-8?Q?...?=
        - Base64 encoding: =?utf-8?B?...?=
        - Multiple encoded parts
        - Plain text (no encoding)

        Args:
            header_value: Raw header value from email

        Returns:
            str: Decoded header value
        """
        if not header_value:
            return ""

        try:
            decoded_parts = decode_header(header_value)

            # Join all decoded parts
            result_parts = []
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    # Decode bytes using the specified encoding or default
                    # to utf-8
                    try:
                        decoded_part = part.decode(encoding or "utf-8")
                    except (UnicodeDecodeError, LookupError):
                        # Fallback to utf-8 if specified encoding fails
                        decoded_part = part.decode("utf-8", errors="replace")
                    result_parts.append(decoded_part)
                else:
                    # Part is already a string
                    result_parts.append(part)

            return "".join(result_parts)

        except Exception as e:
            logger.warning(f"Failed to decode header \"{header_value}\": {e}")
            return header_value

    def _extract_content(self, message) -> Tuple[str, str]:
        """
        Extract text and HTML content from email message.
        Handles multipart messages with superior parsing.

        Returns:
            tuple: (text_content, html_content)
        """
        # Initialize content containers
        text_content = ""
        html_content = ""
        image_placeholders = {}

        # Log the number of parts in the email message for debugging
        logger.debug(
            "Processing email message, parts: %d",
            len(list(message.walk()))
        )

        # Extract all text parts
        text_parts = []
        html_parts = []

        for part in message.walk():
            # Extract common variables for debugging and processing
            content_type = f"{part.content_type.main}/{part.content_type.sub}"
            content_disposition = (
                part.content_disposition.value if part.content_disposition
                else "None"
            )
            has_body = bool(part.body)
            body_size = len(part.body) if part.body else 0

            # Debug log for text content extraction
            logger.debug(
                f"Processing part for text content - "
                f"content_type: {content_type}, "
                f"content_disposition: {content_disposition}, "
                f"has_body: {has_body}, body_size: {body_size}"
            )

            if part.content_type.main == "text":
                # Skip parts marked as attachments
                if content_disposition == "attachment":
                    continue

                if part.content_type.sub == "plain":
                    part_content = self._get_part_content(part)
                    if part_content.strip():
                        text_parts.append(part_content)
                elif part.content_type.sub == "html":
                    part_content = self._get_part_content(part)
                    if part_content.strip():
                        html_parts.append(part_content)

        # Combine all text parts with proper spacing
        if text_parts:
            text_content = "\n\n".join(text_parts)

        # Use the first HTML part as main content
        if html_parts:
            html_content = html_parts[0]

        # Extract inline images and create placeholders
        image_placeholders = self._extract_inline_images(message)

        # Embed image references in text content
        text_content = self._extract_text_with_images(
            text_content, html_content, image_placeholders
        )

        logger.debug(f"Extracted text content: {len(text_content)} chars")

        return text_content, html_content

    def _get_part_content(self, part) -> str:
        """
        Get content from email part with proper decoding.

        Args:
            part: Email part object

        Returns:
            str: Decoded content as string
        """
        try:
            if part.body:
                # Handle both string and bytes content
                if isinstance(part.body, bytes):
                    # Get charset from content type parameters
                    charset = "utf-8"
                    if hasattr(part.content_type, "params"):
                        charset = part.content_type.params.get(
                            "charset", "utf-8")

                    try:
                        content = part.body.decode(charset, errors="ignore")
                    except (UnicodeDecodeError, LookupError):
                        content = part.body.decode("utf-8", errors="ignore")
                else:
                    content = str(part.body)

                # Clean HTML entities from plain text content
                if part.content_type.sub == "plain":
                    content = self._clean_html_entities(content)

                return content
            return ""
        except Exception as e:
            logger.warning(f"Failed to decode email part: {e}")
            return ""

    def _extract_inline_images(self, message) -> Dict[str, Dict[str, Any]]:
        """
        Extract image information from email message.

        This method processes both inline images and regular attachments
        that are images, allowing for better image positioning in text.

        Returns:
            dict: Dictionary mapping placeholder to image info
        """
        inline_images = {}
        processed_md5s = set()

        for part in message.walk():
            # Extract common variables for debugging and processing
            content_type = f"{part.content_type.main}/{part.content_type.sub}"
            content_disposition = (
                part.content_disposition.value if part.content_disposition
                else "None"
            )
            has_body = bool(part.body)
            body_size = len(part.body) if part.body else 0

            # Extract image-specific variables
            content_id = ""
            if hasattr(part.headers, "get"):
                content_id = str(part.headers.get("content-id", "")).strip("<>")

            filename = None
            if hasattr(part.content_disposition, "params"):
                filename = part.content_disposition.params.get("filename")
            elif hasattr(part.content_type, "params"):
                filename = part.content_type.params.get("name")

            # Debug log for inline images extraction
            logger.debug(
                f"Processing part for inline images - "
                f"content_type: {content_type}, "
                f"content_disposition: {content_disposition}, "
                f"content_id: {content_id or 'None'}, "
                f"filename: {filename or 'None'}, "
                f"has_body: {has_body}, body_size: {body_size}"
            )

            # Check if part is an image using both MIME type and file
            # signature detection
            if has_body:
                # Detect file type once and reuse the result
                detected_type, file_extension = self._detect_file_type(
                    part.body, part.content_type.sub, filename
                )

                # Check if it's an image using both MIME type and file signature
                is_image_by_mime = part.content_type.main == "image"
                is_image_by_signature = detected_type.startswith("image/")
                is_image = is_image_by_mime or is_image_by_signature

                if is_image:
                    logger.debug(f"Detected image - MIME: {is_image_by_mime}, "
                                 f"Signature: {is_image_by_signature}, "
                                 f"detected_type: {detected_type}")

                    # Ensure content is in bytes format for MD5 hashing
                    if isinstance(part.body, bytes):
                        body_bytes = part.body
                    else:
                        body_bytes = part.body.encode("utf-8")
                    file_md5 = hashlib.md5(body_bytes).hexdigest()

                    # Skip if we've already processed this image content
                    if file_md5 in processed_md5s:
                        logger.debug(f"Skipping duplicate image with "
                                     f"MD5: {file_md5}")
                        continue

                    # Validate image attachment (apply same filters as
                    # _process_attachments)
                    is_valid, validation_reason = (
                        self._validate_image_attachment(
                            body_bytes, filename
                        )
                    )

                    # Record MD5 after validation to avoid re-processing
                    # (whether valid or invalid)
                    processed_md5s.add(file_md5)

                    if not is_valid:
                        logger.debug(
                            f"Skipping invalid inline image: "
                            f"{filename or file_md5[:8]} "
                            f"({validation_reason})"
                        )
                        continue

                    safe_filename = f"{file_md5}{file_extension}"
                    placeholder = f"[IMAGE: {safe_filename}]"

                    info = {
                        "placeholder": placeholder,
                        "filename": filename,
                        "safe_filename": safe_filename,
                        "content_id": content_id,
                        "content_type": str(part.content_type),
                        "size": body_size,
                        "is_inline": True,
                        "content_disposition": content_disposition
                    }

                    # Store image info by content_id for inline references
                    if content_id:
                        inline_images[content_id] = info
                        # Also store by safe_filename for fallback, but
                        # avoid duplication
                        if safe_filename not in inline_images:
                            inline_images[safe_filename] = info
                    else:
                        # Only store by safe_filename if no content_id
                        inline_images[safe_filename] = info

        return inline_images

    def _extract_text_with_images(
        self, text_content: str, html_content: str, image_placeholders: dict
    ) -> str:
        """
        Extract text content with embedded image placeholders.

        Strategy:
        1. If HTML content exists, use BeautifulSoup for precise image
           positioning
        2. If no HTML, embed images in plain text as fallback

        Args:
            text_content: Current text content
            html_content: Current HTML content
            image_placeholders: Dictionary of image information

        Returns:
            str: Text content with embedded image placeholders
        """
        # Store HTML content for image positioning algorithm
        self._last_html_content = html_content

        # Case 1: HTML content with images - use precise positioning
        if html_content and image_placeholders:
            return self._extract_text_with_html_images(
                text_content, html_content, image_placeholders
            )

        # Case 2: HTML content without images - extract clean text
        elif html_content:
            return self._extract_text_from_html(text_content, html_content)

        # Case 3: Plain text with images - append at end
        elif text_content and image_placeholders:
            return self._embed_images_in_text(text_content, image_placeholders)

        # Case 4: Plain text without images - return as is
        return text_content

    def _extract_text_with_html_images(
        self, text_content: str, html_content: str, image_placeholders: dict
    ) -> str:
        """
        Extract text with images using HTML structure for precise positioning.
        Uses EmailImageProcessor's proven methods to avoid code duplication.
        """
        try:
            # Use EmailImageProcessor's methods to avoid code duplication
            # Step 1: Normalize HTML img tags to placeholders
            html_with_placeholders = self.image_processor._normalize_html_img_tags(
                html_content, image_placeholders
            )

            # Step 2: Extract text from HTML with embedded placeholders
            extracted_text = self._extract_text_with_placeholders(
                html_with_placeholders)

            # Check if any images were actually embedded in the HTML
            if extracted_text and '[IMAGE:' in extracted_text:
                logger.info("Successfully positioned images using "
                            "EmailImageProcessor")
                return extracted_text
            else:
                # No images were embedded in HTML, append them at the end
                logger.info("No images found in HTML, appending at end")
                return self._embed_images_in_text(
                    text_content, image_placeholders)

        except Exception as e:
            logger.warning(f"Failed to position images using "
                           f"EmailImageProcessor: {e}")
            # Fallback to simple image embedding
            return self._embed_images_in_text(text_content, image_placeholders)

    def _extract_text_with_placeholders(self, html_content: str) -> str:
        """
        Extract clean text content from HTML preserving embedded placeholders.

        This method preserves [IMAGE: ...] placeholders that were embedded
        in the HTML.

        Args:
            html_content: HTML content with embedded image placeholders

        Returns:
            str: Clean text content with preserved image placeholders
        """
        try:

            # Step 1: Remove script and style elements
            html_content = re.sub(
                r'<script[^>]*>.*?</script>', '', html_content,
                flags=re.DOTALL | re.IGNORECASE
            )
            html_content = re.sub(
                r'<style[^>]*>.*?</style>', '', html_content,
                flags=re.DOTALL | re.IGNORECASE
            )

            # Step 2: Convert HTML tags to text formatting
            html_content = re.sub(r'<br\s*/?>', '\n', html_content,
                                flags=re.IGNORECASE)
            html_content = re.sub(r'</p>', '\n\n', html_content,
                                flags=re.IGNORECASE)
            html_content = re.sub(r'</div>', '\n', html_content,
                                flags=re.IGNORECASE)

            # Step 2.5: Convert external links to markdown format before
            # removing tags. Convert <a href="url">text</a> to [text](url)
            # for external links only
            def convert_link(match):
                href = match.group(1)
                text = match.group(2)
                # Only convert external links (http/https)
                if href.startswith(('http://', 'https://')):
                    return f"[{text}]({href})"
                else:
                    # For internal links, just return the text
                    return text

            html_content = re.sub(
                r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>([^<]*)</a>',
                convert_link, html_content, flags=re.IGNORECASE)

            # Step 3: Remove all remaining HTML tags but preserve image placeholders
            text_content = re.sub(r'<[^>]+>', '', html_content)

            # Step 4: Decode HTML entities
            text_content = html.unescape(text_content)

            # Step 5: Clean up whitespace while preserving image placeholders
            # Split by image placeholders to handle them separately
            parts = re.split(r'(\[IMAGE:[^\]]+\])', text_content)

            # Clean each part and reassemble
            cleaned_parts = []
            for part in parts:
                if part.startswith('[IMAGE:'):
                    # This is an image placeholder, keep it as is
                    cleaned_parts.append(part)
                else:
                    # This is regular text, clean it up
                    cleaned_part = re.sub(r'\n\s*\n', '\n\n', part)
                    cleaned_part = re.sub(r'[ \t]+', ' ', cleaned_part)
                    cleaned_part = re.sub(r'\n +', '\n', cleaned_part)
                    cleaned_parts.append(cleaned_part)

            # Join parts back together
            text_content = ''.join(cleaned_parts)

            return text_content.strip()

        except Exception as e:
            logger.warning(f"Failed to extract text from HTML with "
                           f"placeholders: {e}")
            return ''

    def _extract_text_from_html(
        self, text_content: str, html_content: str
    ) -> str:
        """
        Extract clean text from HTML when no images are present.
        """
        try:
            soup = BeautifulSoup(html_content, "html.parser")

            extracted_text = self._normalize_text(soup.get_text())
            if extracted_text.strip():
                return extracted_text.strip()
            else:
                return text_content
        except Exception as e:
            logger.warning(f"Failed to extract text from HTML: {e}")
            return text_content


    def _normalize_text(self, text: str) -> str:
        """
        Normalize whitespace in extracted text.
        """
        # Remove excessive blank lines
        text = re.sub(r"\n\s*\n", "\n\n", text)
        # Normalize spaces and tabs
        text = re.sub(r"[ \t]+", " ", text)
        # Remove leading spaces from lines
        text = re.sub(r"\n +", "\n", text)
        return text

    def _embed_images_in_text(
        self,
        text_content: str,
        image_placeholders: dict
    ) -> str:
        """
        Embed image references in text content.

        Strategy:
        1. If HTML content is available, use positioning algorithm
        2. If HTML content is not available, append image references
           at the end of the text as a fallback.

        Args:
            text_content: Text content to embed images into
            image_placeholders: Dictionary of image information

        Returns:
            str: Text content with embedded image references
        """
        # Check if HTML has actual image references
        html_content = getattr(self, "_last_html_content", "")
        has_html_images = False

        if html_content:
            # Check if HTML contains <img> tags or image references
            has_html_images = bool(
                re.search(r'<img[^>]*>', html_content, re.IGNORECASE))

        if has_html_images:
            logger.info(
                "Using HTML positioning algorithm with %d images",
                len(image_placeholders)
            )
            # Use EmailImageProcessor for consistent image positioning
            return self.image_processor.process_images(
                text_content,
                html_content,
                image_placeholders
            )
        else:
            # Try to intelligently position images based on text patterns
            logger.info(
                f"No HTML image references found, attempting intelligent "
                f"positioning for {len(image_placeholders)} images"
            )
            return self.image_processor.process_images(
                text_content, "", image_placeholders)

    def _clean_html_entities(self, text: str) -> str:
        """
        Clean HTML entities from text content.

        Args:
            text: Text content that may contain HTML entities

        Returns:
            str: Cleaned text content
        """
        # Decode HTML entities to plain text
        text = html.unescape(text)

        # Normalize line endings to Unix format
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Remove excessive blank lines and normalize spacing
        text = re.sub(r"\n{2,}", "\n", text)

        # Remove trailing whitespace from each line
        text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)

        # Remove leading whitespace from each line
        text = re.sub(r"^[ \t]+", "", text, flags=re.MULTILINE)

        # Remove trailing empty lines at the end of content
        text = re.sub(r"\n+$", "", text)

        return text.strip()

    def _validate_image_attachment(
        self,
        payload: bytes,
        filename: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Validate image attachment against filtering criteria.

        This method validates image attachments to identify decorative or
        non-essential images (like emojis, icons) that should be excluded
        from processing.

        Current validation criteria:
        1. File size check (faster, checked first)
        2. Image dimensions check (width and height)
        3. Aspect ratio check (filters extreme ratios like dividers, banners)

        Args:
            payload: Image file content as bytes
            filename: Optional filename for logging purposes

        Returns:
            Tuple of (is_valid: bool, reason: str)
            - is_valid: True if image passes validation, False otherwise
            - reason: Explanation of why image failed validation
              (empty if validation passed)
        """
        file_size = len(payload)

        # Check file size first (faster check)
        if file_size < self.MIN_IMAGE_ATTACHMENT_SIZE:
            return False, (
                f"file size too small "
                f"({file_size} bytes < "
                f"{self.MIN_IMAGE_ATTACHMENT_SIZE} bytes)"
            )

        # Check image dimensions and aspect ratio
        try:
            with Image.open(BytesIO(payload)) as image_obj:
                width, height = image_obj.size

                # Validate dimensions are non-zero
                if width == 0 or height == 0:
                    return False, (
                        f"image has invalid dimensions "
                        f"({width}x{height})"
                    )

                # Check minimum dimensions
                if (width < self.MIN_IMAGE_WIDTH or
                        height < self.MIN_IMAGE_HEIGHT):
                    return False, (
                        f"image dimensions too small "
                        f"({width}x{height} < "
                        f"{self.MIN_IMAGE_WIDTH}x"
                        f"{self.MIN_IMAGE_HEIGHT})"
                    )

                # Check aspect ratio (filters dividers, banners, etc.)
                aspect_ratio = max(width / height, height / width)
                if aspect_ratio > self.MAX_IMAGE_ASPECT_RATIO:
                    return False, (
                        f"image aspect ratio too extreme "
                        f"({aspect_ratio:.2f} > "
                        f"{self.MAX_IMAGE_ASPECT_RATIO}, "
                        f"dimensions: {width}x{height})"
                    )

        except UnidentifiedImageError as e:
            # If we can't identify the image format, log but consider it valid
            # (might be a valid image in unsupported format)
            logger.debug(
                f"Unidentified image format for "
                f"{filename or 'unknown'}: {e}"
            )
        except Exception as e:
            # Unexpected error reading image, log but consider it valid
            # (might be a valid image in unsupported format)
            logger.warning(
                f"Unexpected error reading image dimensions for "
                f"{filename or 'unknown'}: {type(e).__name__}: {e}"
            )

        # Image passed all validation checks
        return True, ""

    def _clean_invalid_image_placeholders(
        self,
        text_content: str,
        attachments: list
    ) -> str:
        """
        Remove image placeholders from text content that don't have
        corresponding attachments.

        This ensures that filtered images don't leave orphaned placeholders
        in the final text content.

        Args:
            text_content: Text content with image placeholders
            attachments: List of processed attachment information

        Returns:
            str: Text content with invalid placeholders removed
        """
        # Early return for None, empty string, or text without image markers
        if text_content is None or not text_content or '[IMAGE:' not in text_content:
            return text_content

        # Extract all image placeholders from text
        image_placeholder_pattern = r'\[IMAGE:\s*([^\]]+)\]'
        placeholders = re.findall(image_placeholder_pattern, text_content)

        if not placeholders:
            return text_content

        # Create set of valid safe_filenames from attachments
        valid_filenames = set()
        for att in attachments:
            if att.get('is_image'):
                safe_filename = att.get('safe_filename')
                if safe_filename:
                    valid_filenames.add(safe_filename)

        # Remove invalid placeholders using regex for precise matching
        cleaned_content = text_content
        removed_count = 0

        for placeholder_filename in placeholders:
            placeholder_filename = placeholder_filename.strip()
            if placeholder_filename not in valid_filenames:
                # Use regex to match placeholder with optional whitespace
                # This handles variations like [IMAGE: filename] and
                # [IMAGE:filename]
                placeholder_pattern = (
                    r'\[IMAGE:\s*' +
                    re.escape(placeholder_filename) +
                    r'\]'
                )
                # Check if placeholder exists before removing
                if re.search(placeholder_pattern, cleaned_content):
                    cleaned_content = re.sub(
                        placeholder_pattern, "", cleaned_content
                    )
                    removed_count += 1
                    logger.debug(
                        f"Removed invalid image placeholder: "
                        f"[IMAGE: {placeholder_filename}]"
                    )

        if removed_count > 0:
            # Clean up extra whitespace left by removed placeholders
            cleaned_content = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned_content)
            cleaned_content = re.sub(r'[ \t]+\n', '\n', cleaned_content)
            logger.info(
                f"Cleaned {removed_count} invalid image placeholder(s) "
                f"from text content"
            )

        return cleaned_content.strip()

    def _process_attachments(self, message) -> list:
        """
        Process attachments and inline files from email message.

        Args:
            message: Email message object

        Returns:
            list: List of attachment information dictionaries
        """
        attachments = []
        # Track processed attachments by MD5 to avoid duplicates
        processed_md5s = set()

        for part in message.walk():
            # Extract common variables for debugging and processing
            content_type = f"{part.content_type.main}/{part.content_type.sub}"
            content_disposition = (
                part.content_disposition.value if part.content_disposition
                else "None"
            )
            has_body = bool(part.body)
            body_size = len(part.body) if part.body else 0

            # Debug log for attachments processing
            logger.debug(
                f"Processing part for attachments - "
                f"content_type: {content_type}, "
                f"content_disposition: {content_disposition}, "
                f"has_body: {has_body}, body_size: {body_size}"
            )

            # Skip container parts that don't contain actual content
            if part.content_type.main in ["multipart", "message"]:
                continue

            # Determine if this part is an attachment
            is_attachment = False
            filename = None

            # Check content disposition for attachment status
            if part.content_disposition:
                if hasattr(part.content_disposition, "value"):
                    is_attachment = (
                        part.content_disposition.value in [
                            "attachment", "inline"]
                    )
                if hasattr(part.content_disposition, "params"):
                    filename = part.content_disposition.params.get(
                        "filename"
                    )

            # Check content type parameters for filename
            if not filename and hasattr(part.content_type, "params"):
                filename = part.content_type.params.get("name")

            # Consider part as attachment if it has filename or is not
            # text content
            if filename or part.content_type.main not in ["text"]:
                is_attachment = True

            if is_attachment and has_body:
                try:
                    # Ensure payload is in bytes format for MD5 calculation
                    if isinstance(part.body, bytes):
                        payload = part.body
                    else:
                        payload = part.body.encode("utf-8")

                    # Calculate MD5 to check for duplicates
                    file_md5 = hashlib.md5(payload).hexdigest()

                    # Skip if we've already processed this attachment
                    if file_md5 in processed_md5s:
                        logger.debug(f"Skipping duplicate attachment "
                                     f"with MD5: {file_md5}")
                        continue

                    processed_md5s.add(file_md5)

                    # Check if this is an image attachment
                    is_image = part.content_type.main == "image"

                    # Validate image attachment for decorative/non-essential
                    # images
                    if is_image:
                        is_valid, validation_reason = (
                            self._validate_image_attachment(
                                payload, filename
                            )
                        )

                        if not is_valid:
                            display_filename = (
                                filename or f"unnamed_image_{file_md5[:8]}"
                            )
                            logger.info(
                                f"Skipping invalid image attachment: "
                                f"{display_filename} ({validation_reason})"
                            )
                            continue

                    # Generate filename if not provided
                    if not filename:
                        _, ext = self._detect_file_type(
                            part.body, part.content_type.sub, ""
                        )
                        if not ext:
                            ext = ".bin"
                        filename = f"attachment_{len(attachments) + 1}{ext}"

                    attachment_info = self._save_attachment(
                        filename, str(part.content_type), payload
                    )
                    if attachment_info:
                        attachments.append(attachment_info)
                        logger.info(f"Successfully processed "
                                    f"attachment: {filename}")
                    else:
                        logger.warning(f"Failed to save attachment: {filename}")

                except Exception as e:
                    logger.error(f"Error processing attachment: {e}")
                    continue

        logger.info(f"Total attachments processed: {len(attachments)}")
        return attachments

    def _save_attachment(
        self,
        filename: str,
        content_type: str,
        payload: bytes
    ) -> Optional[Dict]:
        """
        Save attachment to disk and return metadata.

        Args:
            filename: Original filename
            content_type: MIME content type
            payload: File content as bytes

        Returns:
            dict: Attachment metadata or None if failed
        """
        try:
            # Create attachment storage directory
            os.makedirs(self.attachment_dir, exist_ok=True)

            # Generate MD5 hash for consistent filename
            if isinstance(payload, str):
                payload_bytes = payload.encode("utf-8")
            else:
                payload_bytes = payload
            file_md5 = hashlib.md5(payload_bytes).hexdigest()

            # Detect file type and extension with priority logic
            _, file_extension = self._detect_file_type(
                payload, content_type, filename
            )

            safe_filename = f"{file_md5}{file_extension}"

            # Check if file with same MD5 already exists
            file_path = os.path.join(
                self.attachment_dir, safe_filename
            )

            if os.path.exists(file_path):
                logger.debug(f"File with same MD5 already exists: "
                             f"{safe_filename}")
            else:
                # Write new file to disk
                with open(file_path, "wb") as f:
                    f.write(payload)
                logger.debug(f"Saved new file with MD5: {safe_filename}")

            logger.info(
                f"Attachment \"{filename}\" processed successfully, "
                f"size={len(payload)} bytes, MD5: {file_md5}"
            )

            # Determine if file is an image using content detection
            is_image = self._is_image_file(payload, content_type, filename)

            # Get corrected content type based on file signature detection
            detected_type, _ = self._detect_file_type(payload)
            if detected_type != "application/octet-stream":
                corrected_content_type = detected_type
            else:
                corrected_content_type = content_type

            return {
                "filename": filename,
                "safe_filename": safe_filename,
                "content_type": corrected_content_type,
                "file_size": len(payload),
                "file_path": file_path,
                "is_image": is_image
            }

        except Exception as e:
            logger.error(f"Error saving attachment \"{filename}\": {e}")
            return None
