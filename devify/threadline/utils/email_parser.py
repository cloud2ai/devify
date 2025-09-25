"""
⚠️  DEPRECATED PARSER  ⚠️

This parser is OBSOLETE and will be removed in a future version.
Please use EmailFlankerParser instead for better functionality.

Unified Email Parser for processing raw email content
Handles parsing from bytes, files, and strings
"""

import hashlib
import html
import logging
import os
import re
from datetime import datetime
from email import message_from_bytes
from email.header import decode_header
from email.utils import parsedate_to_datetime
from html import unescape
from typing import Any, Dict, List, Optional

from django.utils import timezone
from email_validator import EmailNotValidError, validate_email

from .email_image_parser import process_email_images, HTML_IMG_PATTERNS

logger = logging.getLogger(__name__)


class EmailParser:
    """
    Unified email parser for processing raw email content.
    Handles parsing from bytes, files, and strings.

    .. warning::
        **This parser is OBSOLETE and will be removed in a future version.**

        Please use :class:`EmailFlankerParser` instead, which provides:

        - Better image positioning and embedding
        - Intelligent link preservation (external links as Markdown format)
        - Improved HTML to text conversion
        - Enhanced attachment processing
        - More accurate content extraction

        Migration example:

        .. code-block:: python

            # OLD (obsolete)
            from devify.threadline.utils.email_parser import EmailParser
            parser = EmailParser()

            # NEW (recommended)
            from devify.threadline.utils.email_flanker_parser import EmailFlankerParser
            parser = EmailFlankerParser()
    """

    EMAIL_ATTACHMENT_PREFIX = 'email_attachment_'
    IMAGE_CONTENT_TYPE_PREFIX = 'image/'

    def __init__(
        self, attachment_storage_path: str = '/tmp/attachments'
    ):
        """
        Initialize email parser.

        .. warning::
            This parser is OBSOLETE. Use :class:`EmailFlankerParser` instead.

        Args:
            attachment_storage_path: Path for storing email attachments
        """
        import warnings
        warnings.warn(
            "EmailParser is obsolete and will be removed in a future version. "
            "Please use EmailFlankerParser instead for better functionality.",
            DeprecationWarning,
            stacklevel=2
        )
        self.attachment_storage_path = attachment_storage_path

    def parse_from_bytes(self, email_data: bytes) -> Optional[Dict]:
        """
        Parse email from raw bytes data.

        Args:
            email_data: Raw email data as bytes

        Returns:
            Parsed email data dictionary or None if parsing fails
        """
        try:
            # Parse email using Python's email module
            msg = message_from_bytes(email_data)

            # Extract and decode basic email information
            subject = self._decode_header(msg.get('subject', ''))
            sender = self._decode_header(msg.get('from', ''))
            recipients = self._decode_header(msg.get('to', ''))
            date_str = msg.get('date', '')

            # Parse date
            try:
                received_at = parsedate_to_datetime(date_str)
                if timezone.is_naive(received_at):
                    received_at = timezone.make_aware(received_at)
            except Exception:
                received_at = timezone.now()

            # Extract text and HTML content
            text_content, html_content = (
                self._extract_content_from_email(msg)
            )

            # Generate stable message_id
            stable_message_id = self._generate_stable_message_id(
                subject, sender, recipients, received_at
            )

            # Process attachments
            attachments = self._process_attachments_from_email(msg)

            return {
                'message_id': stable_message_id,
                'subject': subject,
                'sender': sender,
                'recipients': recipients,
                'received_at': received_at,
                'raw_content': email_data.decode(
                    'utf-8', errors='ignore'
                ),
                'html_content': html_content,
                'text_content': text_content,
                'content': text_content or html_content or '',
                'attachments': attachments
            }

        except Exception as e:
            logger.error(f"Failed to parse email: {e}")
            return None

    def parse_from_file(self, file_path: str) -> Optional[Dict]:
        """
        Parse email from file.

        Args:
            file_path: Path to email file

        Returns:
            Parsed email data dictionary or None if parsing fails
        """
        try:
            with open(file_path, 'rb') as f:
                email_data = f.read()
            return self.parse_from_bytes(email_data)
        except Exception as e:
            logger.error(
                f"Failed to parse email from file {file_path}: {e}"
            )
            return None

    def parse_from_string(self, raw_content: str) -> Optional[Dict]:
        """
        Parse email from string content.

        Args:
            raw_content: Raw email content as string

        Returns:
            Parsed email data dictionary or None if parsing fails
        """
        try:
            email_data = raw_content.encode('utf-8')
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

    def _generate_stable_message_id(self, subject: str, sender: str,
                                   recipients: str, received_at) -> str:
        """
        Generate a stable unique message_id using key email fields.
        """
        base = (
            f"{subject}|{sender}|{recipients}|"
            f"{received_at.isoformat()}"
        )
        msg_hash = hashlib.sha256(base.encode('utf-8')).hexdigest()[:16]
        return f"email_{msg_hash}"

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
            return ''

        try:
            decoded_parts = decode_header(header_value)

            # Join all decoded parts
            result_parts = []
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    # Decode bytes using the specified encoding or
                    # default to utf-8
                    try:
                        decoded_part = part.decode(encoding or 'utf-8')
                    except (UnicodeDecodeError, LookupError):
                        # Fallback to utf-8 if specified encoding fails
                        decoded_part = part.decode(
                            'utf-8', errors='replace'
                        )
                    result_parts.append(decoded_part)
                else:
                    # Part is already a string
                    result_parts.append(part)

            return ''.join(result_parts)

        except Exception as e:
            logger.warning(
                f"Failed to decode header '{header_value}': {e}"
            )
            return header_value

    def _extract_content_from_email(self, msg) -> (str, str):
        """
        Extract text and HTML content from email message.
        Priority: HTML content first, then extract text from HTML.

        Returns:
            tuple: (text_content, html_content)
        """
        # Initialize content containers
        text_content = ''
        html_content = ''
        image_placeholders = {}

        # Process email based on its structure
        logger.debug(
            f"Processing email is multipart: {msg.is_multipart()}"
        )
        if msg.is_multipart():
            logger.info("Processing multipart email")
            text_content, html_content, image_placeholders = (
                self._process_multipart_email(msg)
            )
        else:
            logger.info("Processing simple email")
            text_content, html_content = self._process_simple_email(msg)

        # Extract text content with embedded images
        text_content = self._extract_text_with_images(
            text_content, html_content, image_placeholders
        )
        logger.debug(f"Extracted text content: {text_content}")

        return text_content, html_content

    def _process_multipart_email(self, msg) -> (str, str, dict):
        """
        Process multipart email (contains multiple parts like text, HTML,
        attachments).

        Args:
            msg: Email message object

        Returns:
            tuple: (text_content, html_content, image_placeholders)
        """
        text_content = ''
        html_content = ''
        image_placeholders = {}

        for part in msg.walk():
            content_type = part.get_content_type()
            logger.info(
                f"Processing multipart email part "
                f"content_type: {content_type}"
            )
            content_disposition = str(
                part.get('Content-Disposition', '')
            )

            # Handle attachments and inline images
            if self._is_attachment_or_image(
                content_type, content_disposition
            ):
                image_info = self._process_image_attachment(part)
                if image_info:
                    placeholder = image_info['placeholder']
                    image_placeholders[placeholder] = image_info
                continue

            # NOTE(Ray): Currently, we only handle the first part of
            # the email to avoid duplicate content.
            if content_type == 'text/html' and not html_content:
                html_content = self._get_part_content(part)
            elif content_type == 'text/plain' and not text_content:
                text_content = self._get_part_content(part)

        return text_content, html_content, image_placeholders

    def _process_simple_email(self, msg) -> (str, str):
        """
        Process simple email (single content type).

        Args:
            msg: Email message object

        Returns:
            tuple: (text_content, html_content)

        Example:
            Input: Simple email with content_type: "text/html"
            Output:
                text_content: ""
                html_content: "<html><body>Hello world</body></html>"
        """
        content_type = msg.get_content_type()
        logger.info(
            f"Processing simple email content_type: {content_type}"
        )

        if content_type == 'text/html':
            return '', self._get_part_content(msg)
        elif content_type == 'text/plain':
            return self._get_part_content(msg), ''
        else:
            return '', ''

    def _detect_image_type(self, payload: bytes, content_type: str,
                          filename: str) -> bool:
        """
        Detect if a file is an image based on file signature
        (magic bytes).

        This method provides more accurate image detection than relying
        solely on MIME types, which can be incorrect in some email
        clients.

        Args:
            payload: File content as bytes
            content_type: MIME content type from email
            filename: Original filename

        Returns:
            bool: True if file is detected as an image based on signature
        """
        if not payload:
            return False

        # Check file signature (magic bytes) for common image formats
        if payload.startswith(b'\x89PNG\r\n\x1a\n'):
            # PNG signature
            return True
        elif payload.startswith(b'\xff\xd8\xff'):
            # JPEG signature
            return True
        elif (payload.startswith(b'GIF87a') or
              payload.startswith(b'GIF89a')):
            # GIF signature
            return True
        elif payload.startswith(b'BM'):
            # BMP signature
            return True
        elif payload.startswith(b'RIFF') and b'WEBP' in payload[:12]:
            # WebP signature
            return True
        elif payload.startswith(b'\x00\x00\x01\x00'):
            # ICO signature
            return True
        elif payload.startswith(b'\x00\x00\x02\x00'):
            # CUR signature
            return True
        elif (payload.startswith(b'II*\x00') or
              payload.startswith(b'MM\x00*')):
            # TIFF signature
            return True
        else:
            # Fall back to MIME type if no signature match
            return content_type.startswith(
                self.IMAGE_CONTENT_TYPE_PREFIX
            )

    def _get_corrected_content_type(
        self,
        payload: bytes,
        content_type: str
    ) -> str:
        """
        Get corrected content type based on file signature.

        This method corrects incorrect MIME types by analyzing the actual
        file signature (magic bytes) rather than relying on the email's
        declared content type.

        Args:
            payload: File content as bytes
            content_type: Original MIME content type from email

        Returns:
            str: Corrected content type based on file signature

        Example:
            Input: payload=b'\x89PNG...', content_type='application/pdf'
            Output: 'image/png'
        """
        if not payload:
            return content_type

        # Check file signature and return appropriate MIME type
        if payload.startswith(b'\x89PNG\r\n\x1a\n'):
            return 'image/png'
        elif payload.startswith(b'\xff\xd8\xff'):
            return 'image/jpeg'
        elif (payload.startswith(b'GIF87a') or
              payload.startswith(b'GIF89a')):
            return 'image/gif'
        elif payload.startswith(b'BM'):
            return 'image/bmp'
        elif payload.startswith(b'RIFF') and b'WEBP' in payload[:12]:
            return 'image/webp'
        elif payload.startswith(b'\x00\x00\x01\x00'):
            return 'image/x-icon'
        elif payload.startswith(b'\x00\x00\x02\x00'):
            return 'image/x-cursor'
        elif (payload.startswith(b'II*\x00') or
              payload.startswith(b'MM\x00*')):
            return 'image/tiff'
        else:
            # Return original content type if no signature match
            return content_type

    def _is_attachment_or_image(self, content_type: str,
                                content_disposition: str) -> bool:
        """
        Check if email part is an attachment or inline image.

        Args:
            content_type: MIME content type (e.g., "image/jpeg",
                          "application/pdf")
            content_disposition: Content disposition header (e.g.,
                                 "inline", "attachment")

        Returns:
            bool: True if part is attachment or image

        Example:
            - content_type: "image/jpeg", content_disposition:
              "inline" -> True
            - content_type: "application/pdf", content_disposition:
                            "attachment" -> True
            - content_type: "text/plain", content_disposition:
              "" -> False
        """
        return (
            'attachment' in content_disposition or
            'inline' in content_disposition or
            content_type.startswith('image/')
        )

    def _process_image_attachment(self, part) -> Optional[Dict]:
        """
        Process image attachment and return placeholder information.

        Args:
            part: Email part containing the image

        Returns:
            dict: Image placeholder information or None if processing
            fails

        Example:
            Input: Image part with filename "screenshot.jpg" and
                   Content-ID "ii_19863421a764cff311"
            Output: {
                'placeholder': (
                    "[IMAGE: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6.jpg]"
                ),
                'filename': 'screenshot.jpg',
                'safe_filename': 'a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6.jpg',
                'content_id': 'ii_19863421a764cff311',
                'content_type': 'image/jpeg',
                'is_inline': True,
                'content_disposition': 'inline'
            }
        """
        filename = part.get_filename()
        content_id = part.get('Content-ID', '')

        # For inline images, we need either filename or content_id
        if not filename and not content_id:
            return None

        content_type = part.get_content_type()
        content_disposition = str(part.get('Content-Disposition', ''))

        # Generate MD5-based filename for consistency
        # This ensures same content always has same safe_filename
        payload = part.get_payload(decode=True)
        if not payload:
            logger.warning(f"No payload available for image attachment: "
                           f"{filename}")
            return None

        file_md5 = hashlib.md5(payload).hexdigest()
        file_extension = (
            os.path.splitext(filename)[1] if filename else ''
        )
        safe_filename = f"{file_md5}{file_extension}"

        placeholder = f"[IMAGE: {safe_filename}]"

        return {
            'placeholder': placeholder,
            'filename': filename,
            'safe_filename': safe_filename,
            'content_id': content_id.strip('<>') if content_id else None,
            'content_type': content_type,
            'is_inline': 'inline' in content_disposition,
            'content_disposition': content_disposition
        }

    def _extract_text_with_images(
        self,
        text_content: str,
        html_content: str,
        image_placeholders: dict
    ) -> str:
        """
        Extract text content with embedded image placeholders.

        Strategy:
        1. If HTML content exists, embed image placeholders directly
           in HTML
           and extract text
        2. If no HTML, embed images in plain text as fallback

        Args:
            text_content: Current text content
            html_content: Current HTML content
            image_placeholders: Dictionary of image information

        Returns:
            str: Text content with embedded image placeholders
        """
        # Store HTML content for image positioning
        self._last_html_content = html_content

        # Strategy 1: HTML priority - embed images in HTML and
        # extract text
        if html_content and image_placeholders:
            # Embed image placeholders directly in HTML
            html_with_placeholders = self._embed_placeholders_in_html(
                html_content, image_placeholders
            )

            # Extract text from HTML with embedded placeholders
            extracted_text = self._extract_text_with_placeholders(
                html_with_placeholders)
            if extracted_text:
                text_content = extracted_text

        elif html_content:
            # No images, just extract text from HTML
            extracted_text = self._extract_text_from_html(html_content)
            if extracted_text:
                text_content = extracted_text

        # Strategy 2: Fallback - embed images in plain text
        elif text_content and image_placeholders:
            text_content = self._embed_images_in_text(
                text_content, image_placeholders
            )

        return text_content

    def _embed_placeholders_in_html(self, html_content: str,
                                    image_placeholders: dict) -> str:
        """
        Embed image placeholders directly in HTML content.

        This method replaces <img src="cid:..."> and
        <img src="file://..."> tags
        with placeholder text that will be preserved during HTML-to-text conversion.
        Also handles Chinese image references like [图片: filename(description)]

        Args:
            html_content: Original HTML content
            image_placeholders: Dictionary of image information

        Returns:
            str: HTML content with embedded placeholders

        Example:
            Input:
                html_content: "<p>Hello <img src='cid:image1.jpg'> world</p>"
                image_placeholders: {"[IMAGE: a1b2c3d4_image1.jpg]": {...}}
            Output:
                "<p>Hello [IMAGE: a1b2c3d4_image1.jpg] world</p>"
        """
        result_html = html_content

        # Replace each <img> tag with its corresponding placeholder
        for placeholder, image_info in image_placeholders.items():
            # Get both filename and content_id for matching
            safe_filename = image_info['safe_filename']
            original_filename = image_info['filename']
            content_id = image_info.get('content_id')


            # Create patterns to match the img tag using constants
            patterns = []

            # Pattern 1: Match by original filename (for cid: protocol)
            if original_filename:
                filename_without_ext = os.path.splitext(original_filename)[0]
                patterns.extend([
                    HTML_IMG_PATTERNS['CID_BY_FILENAME'].format(
                        filename=re.escape(original_filename)
                    ),
                    HTML_IMG_PATTERNS['CID_BY_FILENAME_NO_EXT'].format(
                        filename_no_ext=re.escape(filename_without_ext)
                    )
                ])

            # Pattern 2: Match by content_id (for complex CID formats)
            if content_id:
                patterns.append(HTML_IMG_PATTERNS['CID_BY_CONTENT_ID'].format(
                    content_id=re.escape(content_id)
                ))

            # Pattern 3: Match by safe_filename (fallback)
            patterns.append(HTML_IMG_PATTERNS['CID_BY_SAFE_FILENAME'].format(
                safe_filename=re.escape(safe_filename)
            ))

            # Pattern 4: Match file:// protocol images by filename
            if original_filename:
                filename_without_ext = os.path.splitext(original_filename)[0]
                patterns.extend([
                    HTML_IMG_PATTERNS['FILE_BY_FILENAME'].format(
                        filename=re.escape(original_filename)
                    ),
                    HTML_IMG_PATTERNS['FILE_BY_FILENAME_NO_EXT'].format(
                        filename_no_ext=re.escape(filename_without_ext)
                    )
                ])

            # Pattern 5: Match by img id attribute (for complex cases)
            if original_filename:
                filename_without_ext = os.path.splitext(original_filename)[0]
                patterns.extend([
                    HTML_IMG_PATTERNS['ID_BY_FILENAME'].format(
                        filename=re.escape(original_filename)
                    ),
                    HTML_IMG_PATTERNS['ID_BY_FILENAME_NO_EXT'].format(
                        filename_no_ext=re.escape(filename_without_ext)
                    )
                ])

            # Try to match and replace
            for pattern in patterns:
                if re.search(pattern, result_html):
                    # Use safe_filename for the placeholder to ensure consistency
                    safe_placeholder = f"[IMAGE: {safe_filename}]"
                    result_html = re.sub(pattern, safe_placeholder, result_html)
                    logger.debug(f"Replaced {pattern} with {safe_placeholder}")
                    break

        # Note: Text-based image references in HTML will be handled later
        # by the process_email_images function during text extraction

        return result_html

    def _extract_text_with_placeholders(self, html_content: str) -> str:
        """
        Extract clean text content from HTML while preserving embedded placeholders.

        This method is similar to _extract_text_from_html but preserves
        [IMAGE: ...] placeholders that were embedded in the HTML.

        Args:
            html_content: HTML content with embedded image placeholders

        Returns:
            str: Clean text content with preserved image placeholders

        Example:
            Input HTML:
                <html>
                <body>
                    <h1>Hello World</h1>
                    <p>This is a test email with an image:</p>
                    [IMAGE: a1b2c3d4_image1.jpg]
                    <p>End of message.</p>
                </body>
                </html>

            Output text:
                Hello World

                This is a test email with an image:
                [IMAGE: a1b2c3d4_image1.jpg]
                End of message.
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

            # Step 3: Remove all remaining HTML tags but preserve image placeholders
            # Use a more sophisticated approach to preserve [IMAGE: ...] placeholders
            text_content = re.sub(r'<[^>]+>', '', html_content)

            # Step 4: Decode HTML entities
            text_content = unescape(text_content)

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

    def _get_part_content(self, part) -> str:
        """
        Get content from email part with proper decoding.

        This method handles various encoding issues and ensures proper
        text extraction from email parts.

        Args:
            part: Email part object

        Returns:
            str: Decoded content as string

        Example:
            Input: Email part with:
                - payload: b'Hello \xc3\xa9 world' (UTF-8 encoded)
                - charset: 'utf-8'
                - content_type: 'text/plain'

            Output: "Hello é world"
        """
        try:
            # Get raw payload
            payload = part.get_payload(decode=True)
            if payload is None:
                return ''

            # Get charset from email part
            charset = part.get_content_charset() or 'utf-8'

            # Decode content with proper charset
            try:
                content = payload.decode(charset, errors='ignore')
            except (UnicodeDecodeError, LookupError):
                # Fallback to utf-8 if charset decoding fails
                content = payload.decode('utf-8', errors='ignore')

            # Clean HTML entities from text content
            content_type = part.get_content_type()
            if content_type == 'text/plain':
                content = self._clean_html_entities(content)
            return content
        except Exception as e:
            logger.warning(f"Failed to decode email part: {e}")
            return ''

    def _clean_html_entities(self, text: str) -> str:
        """
        Clean HTML entities from text content.

        Converts HTML entities like &amp;, &lt;, &gt; to their character
        equivalents
        and removes extra whitespace.

        Args:
            text: Text content that may contain HTML entities

        Returns:
            str: Cleaned text content

        Example:
            Input: "Hello &amp; world &lt;test&gt;"
            Output: "Hello & world <test>"
        """

        # Decode HTML entities
        text = html.unescape(text)

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)

        return text.strip()

    def _extract_text_from_html(self, html_content: str) -> str:
        """
        Extract clean text content from HTML while preserving image positions.

        Process:
        1. Remove script and style elements
        2. Replace <img> tags with placeholders before stripping HTML
        3. Convert HTML tags to text formatting
        4. Clean up whitespace and HTML entities

        Args:
            html_content: Raw HTML content from email

        Returns:
            str: Clean text content with image placeholders

        Example:
            Input HTML:
                <html>
                <body>
                    <h1>Hello World</h1>
                    <p>This is a test email with an image:</p>
                    <img src="cid:image1.jpg" alt="Screenshot">
                    <p>End of message.</p>
                </body>
                </html>

            Output text:
                Hello World

                This is a test email with an image:
                [IMAGE: image1.jpg]
                End of message.
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

            # Step 2: Replace images with placeholders before removing HTML tags
            image_placeholders = {}
            img_pattern = r'<img[^>]*src="cid:([^"]+)"[^>]*>'

            def replace_img_with_placeholder(match):
                cid = match.group(1)
                # Use the actual filename as placeholder
                placeholder = f"[IMAGE: {cid}]"
                image_placeholders[placeholder] = cid
                return placeholder

            # Replace <img> tags with placeholders, controlling line length
            html_content = re.sub(
                img_pattern,
                replace_img_with_placeholder,
                html_content
            )

            # Step 3: Convert HTML tags to text formatting
            html_content = re.sub(r'<br\s*/?>', '\n', html_content,
                                flags=re.IGNORECASE)
            html_content = re.sub(r'</p>', '\n\n', html_content,
                                flags=re.IGNORECASE)
            html_content = re.sub(r'</div>', '\n', html_content,
                                flags=re.IGNORECASE)

            # Step 4: Remove all remaining HTML tags
            text_content = re.sub(r'<[^>]+>', '', html_content)

            # Step 5: Decode HTML entities
            text_content = unescape(text_content)

            # Step 6: Clean up whitespace
            text_content = re.sub(r'\n\s*\n', '\n\n', text_content)
            text_content = re.sub(r'[ \t]+', ' ', text_content)
            text_content = re.sub(r'\n +', '\n', text_content)

            return text_content.strip()

        except Exception as e:
            logger.warning(f"Failed to extract text from HTML: {e}")
            return ''

    def _embed_images_in_text(
        self,
        text_content: str,
        image_placeholders: dict
    ) -> str:
        """
        correspond to the original HTML structure.

        Strategy:
        1. If HTML content is available, use a positioning algorithm
           for precise placement of image references.
        2. If HTML content is not available, append image references
           at the end of the text as a fallback.

        Args:
            text_content: Text content to embed images into
            image_placeholders: Dictionary of image information

        Returns:
            str: Text content with embedded image references

        Example:
            Input:
                text_content: "Hello world"
                image_placeholders: {
                    "[IMAGE: image1.jpg]": {'filename': 'image1.jpg', ...},
                    "[IMAGE: image2.png]": {'filename': 'image2.png', ...}
                }
            Output (with HTML positioning):
                "Hello\n[IMAGE: image1.jpg]\nworld\n[IMAGE: image2.png]"

            Output (fallback append):
                "Hello world\n\n[IMAGE: image1.jpg]\n[IMAGE: image2.png]"
        """
        # Strategy 1: Use HTML positioning algorithm if available
        if (
            hasattr(self, "_last_html_content")
            and getattr(self, "_last_html_content", "")
        ):
            logger.info(
                "Using HTML positioning algorithm with %d images",
                len(image_placeholders)
            )
            return process_email_images(
                text_content,
                getattr(self, "_last_html_content", ""),
                image_placeholders
            )
        else:
            # Strategy 2: Fallback - append images at the end
            logger.info(
                f"Appending {len(image_placeholders)} images at the end of text"
            )
            image_references = []
            for placeholder, image_info in image_placeholders.items():
                image_references.append(f"[IMAGE: {image_info['filename']}]")

            if image_references:
                text_content += "\n\n" + "\n".join(image_references)

            return text_content

    def _process_attachments_from_email(self, msg) -> list:
        """
        Process attachments and inline files from email message.

        This method extracts and saves all attachments and inline files from
        the email, including images embedded in HTML content. It generates
        safe filenames with UUID prefixes to avoid conflicts.

        Args:
            msg: Email message object

        Returns:
            list: List of attachment information dictionaries

        Example:
            Input: Email with attachments and inline images:
                - filename: "document.pdf", content_type: "application/pdf",
                            disposition: "attachment"
                - filename: "image001.png", content_type: "image/png",
                            disposition: "inline"

            Output: [
                {
                    'filename': 'document.pdf',
                    'safe_filename': '550e8400-e29b-41d4-a716-446655440000.pdf',
                    'content_type': 'application/pdf',
                    'file_size': 1024,
                    'file_path': '/tmp/attachments/550e8400-e29b-41d4-a716-446655440000.pdf',
                    'is_image': False
                },
                {
                    'filename': 'image001.png',
                    'safe_filename': '6ba7b810-9dad-11d1-80b4-00c04fd430c8.png',
                    'content_type': 'image/png',
                    'file_size': 2048,
                    'file_path': '/tmp/attachments/6ba7b810-9dad-11d1-80b4-00c04fd430c8.png',
                    'is_image': True
                }
            ]
        """
        attachments = []

        for part in msg.walk():
            content_disposition = str(part.get('Content-Disposition', ''))
            content_type = part.get_content_type()
            filename = part.get_filename()

            # Add debug logging
            logger.debug(f"Processing part: content_type={content_type}, "
                        f"content_disposition='{content_disposition}', "
                        f"filename='{filename}'")

            # Process attachments and inline files
            # Some email clients don't set Content-Disposition for inline images
            # So we also check if it's an image with a filename
            is_attachment = (
                'attachment' in content_disposition or
                'inline' in content_disposition or
                (content_type.startswith('image/') and filename)
            )

            if not is_attachment:
                logger.debug(f"Skipping part: not an attachment/inline file")
                continue

            try:
                if not filename:
                    logger.debug(f"Skipping part: no filename")
                    continue

                payload = part.get_payload(decode=True)

                if payload:
                    logger.debug(f"Processing attachment: {filename}, "
                                f"size={len(payload)} bytes")
                    # Save attachment with safe filename
                    attachment_info = self._save_attachment(
                        filename, content_type, payload
                    )
                    if attachment_info:
                        attachments.append(attachment_info)
                        logger.info(f"Successfully processed "
                                    f"attachment: {filename}")
                    else:
                        logger.warning(f"Failed to save attachment: {filename}")
                else:
                    logger.debug(f"Skipping part: no payload")

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

        Example:
            Input:
                filename: "report.pdf"
                content_type: "application/pdf"
                payload: b"%PDF-1.4\n..."

            Output:
                {
                    'filename': 'report.pdf',
                    'safe_filename': 'a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6.pdf',
                    'content_type': 'application/pdf',
                    'file_size': 1024,
                    'file_path': '/tmp/attachments/a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6.pdf',
                    'is_image': False
                }
        """
        try:
            # Create attachment directory
            os.makedirs(self.attachment_storage_path, exist_ok=True)

            # Generate MD5-based filename for consistency
            # This ensures same content always has same safe_filename
            file_md5 = hashlib.md5(payload).hexdigest()
            file_extension = os.path.splitext(filename)[1] if filename else ''
            safe_filename = f"{file_md5}{file_extension}"

            # Check if file already exists with same MD5
            file_path = os.path.join(
                self.attachment_storage_path, safe_filename
            )

            if os.path.exists(file_path):
                logger.debug(f"File with same MD5 already "
                             f"exists: {safe_filename}")
                # File already exists, no need to save again
            else:
                # Save file to disk
                with open(file_path, 'wb') as f:
                    f.write(payload)
                logger.debug(f"Saved new file with MD5: {safe_filename}")

            logger.info(
                f"Attachment '{filename}' processed successfully, "
                f"size={len(payload)} bytes, MD5: {file_md5}"
            )

            # Determine if the file is an image based on its signature
            is_image = self._detect_image_type(payload, content_type, filename)

            # Get corrected content type based on file signature
            corrected_content_type = self._get_corrected_content_type(
                payload, content_type
            )

            return {
                'filename': filename,
                'safe_filename': safe_filename,
                'content_type': corrected_content_type,
                'file_size': len(payload),
                'file_path': file_path,
                'is_image': is_image
            }

        except Exception as e:
            logger.error(f"Error saving attachment '{filename}': {e}")
            return None
