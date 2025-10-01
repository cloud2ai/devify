"""
Advanced Email Image Processing Engine

This module provides a comprehensive image processing engine specifically
designed for email content, handling all image scenarios including
HTML-based positioning, text-based references, and intelligent fallback
mechanisms.

The EmailImageProcessor class encapsulates all email image processing
logic and provides a clean, maintainable interface for handling various
image reference formats in email content.
"""

import logging
import os
import re
from typing import Dict, List, Optional, Tuple

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Image processing constants
DEFAULT_IMAGE_PLACEHOLDER_PREFIX = "[IMAGE:"
DEFAULT_IMAGE_PLACEHOLDER_SUFFIX = "]"
DEFAULT_CID_PROTOCOL = "cid:"
DEFAULT_FILE_PROTOCOL = "file://"
DEFAULT_IMAGE_EXTENSION = ".jpg"

# HTML img tag patterns for image replacement
# HTML <img> tag regex patterns for various matching strategies.
HTML_IMG_PATTERNS = {
    'CID_BY_FILENAME':
        r'<img[^>]*src=["\']cid:{filename}["\'][^>]*>',
    'CID_BY_FILENAME_NO_EXT':
        r'<img[^>]*src=["\']cid:{filename_no_ext}["\'][^>]*>',
    'CID_BY_CONTENT_ID':
        r'<img[^>]*src=["\']cid:{content_id}["\'][^>]*>',
    'CID_BY_SAFE_FILENAME':
        r'<img[^>]*src=["\']cid:{safe_filename}["\'][^>]*>',
    'FILE_BY_FILENAME':
        r'<img[^>]*src=["\']file://[^"\']*{filename}["\'][^>]*>',
    'FILE_BY_FILENAME_NO_EXT':
        r'<img[^>]*src=["\']file://[^"\']*{filename_no_ext}["\'][^>]*>',
    'ID_BY_FILENAME':
        r'<img[^>]*id=["\'][^"\']*{filename}[^"\']*["\'][^>]*>',
    'ID_BY_FILENAME_NO_EXT':
        r'<img[^>]*id=["\'][^"\']*{filename_no_ext}[^"\']*["\'][^>]*>',
}

# Image reference patterns for various languages
IMAGE_REFERENCE_PATTERNS = [
    # Chinese patterns
    r'\[图片:\s*([^\]\(]+)(?:\([^\)]*\))?\]',  # [图片: filename(description)]
    r'\[图片:\s*([^\]]+)\]',  # [图片: filename]
    r'图片(\d+)\s*（可在附件中查看）',  # 图片1（可在附件中查看）
    r'图片(\d+)\s*\(可在附件中查看\)',  # 图片1(可在附件中查看)
    r'图片(\d+)\s*（见附件）',  # 图片1（见附件）
    r'图片(\d+)\s*\(见附件\)',  # 图片1(见附件)
    r'图片(\d+)\s*（附件）',  # 图片1（附件）
    r'图片(\d+)\s*\(附件\)',  # 图片1(附件)

    # Latin-based language patterns (English, Spanish, French, German, etc.)
    r'\[[Ii]mage:\s*([^\]\(]+)(?:\([^\)]*\))?\]',  # [image: filename(description)]
    r'\[[Ii]mage:\s*([^\]]+)\]',  # [image: filename]
    r'\[[Ii]magen:\s*([^\]\(]+)(?:\([^\)]*\))?\]',  # [imagen: filename(description)] (Spanish)
    r'\[[Ii]magen:\s*([^\]]+)\]',  # [imagen: filename] (Spanish)
    r'\[[Bb]ild:\s*([^\]\(]+)(?:\([^\)]*\))?\]',  # [bild: filename(description)] (German)
    r'\[[Bb]ild:\s*([^\]]+)\]',  # [bild: filename] (German)
    r'[Ii]mage\s*(\d+)\s*see\s+attached',  # Image 1 see attached
    r'[Ii]mage\s*(\d+)\s*attached\s+image',  # Image 1 attached image
    r'[Ii]mage\s*(\d+)\s*image\s+attached',  # Image 1 image attached
    r'[Ii]magen\s*(\d+)\s*ver\s+adjunto',  # Imagen 1 ver adjunto (Spanish)
    r'[Bb]ild\s*(\d+)\s*siehe\s+anhäng',  # Bild 1 siehe anhäng (German)
]

# Attachment reference patterns
ATTACHMENT_REFERENCE_PATTERNS = [
    # Chinese
    "（可在附件中查看）", "(可在附件中查看)", "（见附件）", "(见附件)", "（附件）",
    "(附件)",
    # English
    "see attached", "See attached", "attached image", "Attached image",
    "image attached", "Image attached",
    # Spanish
    "ver adjunto", "Ver adjunto", "imagen adjunta", "Imagen adjunta",
    # German
    "siehe anhäng", "Siehe anhäng", "anhäng bild", "Anhäng bild",
    # French
    "voir pièce jointe", "Voir pièce jointe", "image jointe", "Image jointe",
]

# Image prefix patterns
IMAGE_PREFIX_PATTERNS = [
    # Chinese
    "图片", "图",
    # Latin-based languages
    "image", "Image", "img", "Img", "picture", "Picture", "photo", "Photo",
    "imagen", "Imagen", "bild", "Bild", "imagine", "Imagine", "imagem", "Imagem",
]


class EmailImageProcessor:
    """
    Advanced Email Image Processing Engine.

    This class is specifically designed for processing images in email
    content, handling all image scenarios that commonly occur in email
    messages:

    1. CID references (cid:image.jpg) - inline email images
    2. Direct filename references (file://path/image.jpg) - local files
    3. ID-based references (img id="image1") - fallback matching
    4. Text-based references (图片1, Image 1) - text identifiers
    5. Custom pattern matching - filename-based patterns
    6. Position-based insertion - HTML structure positioning
    7. Fallback handling - append to end when all else fails

    The processor intelligently handles various email formats including:
    - HTML emails with embedded images
    - Plain text emails with image references
    - Multi-language email content (Chinese, Latin-based languages)
    - iPhone/Android email client formats

    Configuration:
        All default values are defined as module-level constants for easy
        customization and consistency across the application.

    Attributes:
        image_placeholder_prefix (str): Prefix for image placeholders
        image_placeholder_suffix (str): Suffix for image placeholders
        cid_protocol (str): CID protocol identifier for email attachments
        file_protocol (str): File protocol identifier for local files
        default_image_extension (str): Default image file extension
        image_reference_patterns (List[str]): Regex patterns for image
            references
        attachment_reference_patterns (List[str]): Attachment reference
            patterns
        image_prefix_patterns (List[str]): Image prefix patterns for
            matching
    """

    def __init__(self,
                 image_placeholder_prefix: str =
                     DEFAULT_IMAGE_PLACEHOLDER_PREFIX,
                 image_placeholder_suffix: str =
                     DEFAULT_IMAGE_PLACEHOLDER_SUFFIX,
                 cid_protocol: str = DEFAULT_CID_PROTOCOL,
                 file_protocol: str = DEFAULT_FILE_PROTOCOL,
                 default_image_extension: str = DEFAULT_IMAGE_EXTENSION):
        """
        Initialize the EmailImageProcessor.

        Args:
            image_placeholder_prefix: Prefix for image placeholders in
                email content
            image_placeholder_suffix: Suffix for image placeholders in
                email content
            cid_protocol: CID protocol identifier for email attachments
            file_protocol: File protocol identifier for local file
                references
            default_image_extension: Default image file extension for
                fallback
        """
        self.image_placeholder_prefix = image_placeholder_prefix
        self.image_placeholder_suffix = image_placeholder_suffix
        self.cid_protocol = cid_protocol
        self.file_protocol = file_protocol
        self.default_image_extension = default_image_extension

        # Use extracted constants for patterns
        self.image_reference_patterns = IMAGE_REFERENCE_PATTERNS
        self.attachment_reference_patterns = ATTACHMENT_REFERENCE_PATTERNS
        self.image_prefix_patterns = IMAGE_PREFIX_PATTERNS

        logger.debug("EmailImageProcessor initialized successfully")

    def process_images(self,
                       text_content: str,
                       html_content: str,
                       image_placeholders: Dict) -> str:
        """
        Main image processing method that handles all scenarios.

        Args:
            text_content: Plain text content to embed images into
            html_content: HTML content for position calculation
            image_placeholders: Dictionary of image information

        Returns:
            str: Text content with embedded image references at
                 appropriate positions
        """
        if not image_placeholders:
            logger.debug("No image placeholders to process")
            return text_content

        logger.info(f"Processing {len(image_placeholders)} images with "
                    f"EmailImageProcessor")

        # Try HTML-based positioning first
        if html_content:
            try:
                result = self._process_with_html(
                    text_content, html_content, image_placeholders)
                if result:
                    logger.info("Successfully processed images with HTML "
                               "positioning")
                    return result
            except Exception as e:
                logger.warning(f"HTML processing failed: {e}, "
                               f"falling back to text processing")

        # Fall back to text-based processing
        return self._process_with_text(text_content, image_placeholders)

    def _process_with_html(self,
                           text_content: str,
                           html_content: str,
                           image_placeholders: Dict) -> Optional[str]:
        """
        Process images using HTML structure for positioning.

        Handles scenarios 1-3: CID, filename, and ID references.

        Args:
            text_content: Plain text content
            html_content: HTML content for position calculation
            image_placeholders: Dictionary of image information

        Returns:
            Optional[str]: Processed text content or None if failed
        """
        try:
            # Normalize image references first
            normalized_html = self._normalize_image_references(
                html_content, image_placeholders)

            # Parse HTML and find image positions
            soup = BeautifulSoup(normalized_html, 'html.parser')
            image_positions = self._find_image_positions(
                soup, image_placeholders)

            if image_positions:
                # Insert images at calculated positions
                return self._insert_images_at_positions(
                    text_content, image_positions)
            else:
                # No HTML-based positions found, fall back to text processing
                return None

        except Exception as e:
            logger.error(f"HTML processing failed: {e}")
            return None

    def _process_with_text(self, text_content: str,
                           image_placeholders: Dict) -> str:
        """
        Process images using text-based references.

        Handles scenarios 4-7: Text references, custom patterns, and
        fallback.

        Args:
            text_content: Plain text content
            image_placeholders: Dictionary of image information

        Returns:
            str: Processed text content with images positioned or
                appended
        """
        logger.debug("Processing images with text-based references")

        # First, try intelligent positioning based on text patterns
        intelligent_result = self._intelligently_position_images(
            text_content, image_placeholders)

        # Check if intelligent positioning worked
        positioned_images = self._check_positioned_images(
            intelligent_result, image_placeholders)

        if len(positioned_images) == len(image_placeholders):
            logger.info(f"Successfully positioned all "
                        f"{len(image_placeholders)} images using "
                        f"intelligent positioning")
            return intelligent_result

        # If intelligent positioning didn't work for all images, try other methods
        # First, try to normalize text references
        normalized_content = self._normalize_image_references(
            text_content, image_placeholders)

        # Check if any images were positioned by normalization
        positioned_images = self._check_positioned_images(
            normalized_content, image_placeholders)

        # For remaining images, try custom patterns
        remaining_images = self._get_remaining_images(image_placeholders,
                                                    positioned_images)

        if remaining_images:
            normalized_content = self._process_custom_patterns(
                normalized_content, remaining_images)
            positioned_images = self._check_positioned_images(
                normalized_content, image_placeholders)

        # Append any remaining images at the end
        return self._append_remaining_images(normalized_content,
                                           image_placeholders,
                                           positioned_images)

    def _intelligently_position_images(self, text_content: str,
                                     image_placeholders: Dict) -> str:
        """
        Intelligently position images based on text patterns and order.

        This method tries to position images in logical order based on:
        1. Text patterns like "图片1（可在附件中查看）"
        2. Image order in the email
        3. Fallback to appending at the end

        Args:
            text_content: Text content to embed images into
            image_placeholders: Dictionary of image information

        Returns:
            str: Text content with intelligently positioned images
        """
        if not image_placeholders:
            return text_content

        # Convert image_placeholders to a list for ordered processing
        image_list = []
        for placeholder, image_info in image_placeholders.items():
            image_list.append({
                'placeholder': placeholder,
                'safe_filename': image_info.get('safe_filename', ''),
                'filename': image_info.get('filename', ''),
                'content_id': image_info.get('content_id', '')
            })

        # Sort images by filename to maintain order
        image_list.sort(key=lambda x: x['filename'] or x['safe_filename'])

        result = text_content
        positioned_count = 0

        # Try to position images based on text patterns
        for i, image_info in enumerate(image_list):
            image_placeholder = f"[IMAGE: {image_info['safe_filename']}]"

            # Look for patterns like "图片1（可在附件中查看）", "图片2（可在附件中查看）", etc.
            pattern = f"图片{i+1}（可在附件中查看）"
            if pattern in result:
                # Replace the pattern with the image placeholder
                result = result.replace(pattern, f"{pattern}\n{image_placeholder}")
                positioned_count += 1
                logger.debug(f"Positioned image {i+1} after pattern: {pattern}")
            else:
                # Try other patterns
                alt_patterns = [
                    f"图片{i+1}",
                    f"图片 {i+1}",
                    f"图{i+1}",
                    f"图 {i+1}",
                    f"image{i+1}",
                    f"image {i+1}",
                    f"Image{i+1}",
                    f"Image {i+1}"
                ]

                positioned = False
                for alt_pattern in alt_patterns:
                    if alt_pattern in result:
                        result = result.replace(
                            alt_pattern, f"{alt_pattern}\n{image_placeholder}")
                        positioned_count += 1
                        logger.debug(f"Positioned image {i+1} after pattern: "
                                     f"{alt_pattern}")
                        positioned = True
                        break

                if not positioned:
                    # If no pattern found, append at the end
                    result += f"\n{image_placeholder}"
                    logger.debug(f"Appended image {i+1} at the end")

        logger.info(f"Intelligently positioned {positioned_count} out of "
                    f"{len(image_list)} images")
        return result

    def _normalize_image_references(self, content: str,
                                    image_placeholders: Dict) -> str:
        """
        Normalize image references in content using regex patterns.

        Args:
            content: Content to normalize
            image_placeholders: Dictionary of image information

        Returns:
            str: Content with normalized image references
        """
        if not image_placeholders:
            return content

        logger.debug(f"Normalizing image references for "
                     f"{len(image_placeholders)} images")
        result = content

        # First, handle HTML img tags with CID references
        result = self._normalize_html_img_tags(result, image_placeholders)

        # Then, handle text-based image references
        for pattern in self.image_reference_patterns:
            result = re.sub(pattern,
                            lambda match: self._replace_image_reference(
                              match, pattern, image_placeholders),
                            result)

        logger.debug("Image references normalized successfully")
        return result

    def _normalize_html_img_tags(self, content: str,
                                 image_placeholders: Dict) -> str:
        """
        Normalize HTML img tags with CID references to [IMAGE: ...] format.

        Args:
            content: HTML content to normalize
            image_placeholders: Dictionary of image information

        Returns:
            str: HTML content with normalized image references
        """
        result = content

        # Replace each <img> tag with its corresponding placeholder
        for placeholder, image_info in image_placeholders.items():
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

            # Try to match and replace
            for pattern in patterns:
                if re.search(pattern, result):
                    safe_placeholder = f"[IMAGE: {safe_filename}]"
                    result = re.sub(pattern, safe_placeholder, result)
                    logger.debug(f"Replaced {pattern} with {safe_placeholder}")
                    break

        return result

    def _replace_image_reference(self, match, pattern: str,
                                 image_placeholders: Dict) -> str:
        """
        Replace matched image reference with normalized format.

        Args:
            match: Regex match object
            pattern: Pattern that matched
            image_placeholders: Dictionary of image information

        Returns:
            str: Normalized image reference
        """
        groups = match.groups()
        pattern_info = self._detect_pattern_type(pattern)
        prefix = self._extract_prefix_from_pattern(pattern)

        if pattern_info['has_chinese_chars']:
            return self._process_chinese_reference(groups, prefix,
                                                 image_placeholders)
        elif pattern_info['has_image_keyword']:
            return self._process_latin_reference(groups, prefix,
                                               image_placeholders)

        return match.group(0)

    def _detect_pattern_type(self, pattern: str) -> Dict:
        """Detect pattern type based on regex content analysis."""
        return {
            'has_number_group': r'(\d+)' in pattern,
            'is_bracket_format': '[' in pattern and ']' in pattern,
            'has_colon': ':' in pattern,
            'has_chinese_chars': bool(re.search(r'[\u4e00-\u9fff]', pattern)),
            'has_image_keyword': bool(re.search(
                r'[Ii]mage|[Ii]magen|[Bb]ild|[Ii]magine|[Ii]magem', pattern)),
        }

    def _extract_prefix_from_pattern(self, pattern: str) -> str:
        """Extract the image prefix from regex pattern dynamically."""
        # Extract prefix from bracket format: [图片: ...] or [image: ...]
        bracket_match = re.search(r'\[([^:\]]+):', pattern)
        if bracket_match:
            return bracket_match.group(1)

        # Extract prefix from number format: 图片1 or Image 1
        number_prefix_match = re.search(r'([a-zA-Z\u4e00-\u9fff]+)(?=\d)',
                                       pattern)
        if number_prefix_match:
            return number_prefix_match.group(1)

        # Extract prefix from keyword patterns
        keyword_match = re.search(r'([a-zA-Z\u4e00-\u9fff]+)', pattern)
        if keyword_match:
            return keyword_match.group(1)

        return 'image'  # Default fallback

    def _process_chinese_reference(self, groups: Tuple, prefix: str,
                                  image_placeholders: Dict) -> str:
        """Process Chinese image reference."""
        if not groups:
            return ""

        if len(groups) == 1 and groups[0].isdigit():
            # Number format: 图片1
            image_number = groups[0]
            safe_filename = self._find_image_by_number(image_number,
                                                     image_placeholders,
                                                     prefix)

            if safe_filename:
                return (f"{self.image_placeholder_prefix} {safe_filename}"
                       f"{self.image_placeholder_suffix}")
            else:
                return (f"{self.image_placeholder_prefix} {prefix}"
                       f"{image_number}{self.default_image_extension}"
                       f"{self.image_placeholder_suffix}")
        else:
            # Filename format: [图片: filename]
            filename = groups[0].strip()
            safe_filename = self._find_image_by_filename(filename,
                                                       image_placeholders)

            if safe_filename:
                return (f"{self.image_placeholder_prefix} {safe_filename}"
                       f"{self.image_placeholder_suffix}")
            else:
                return (f"{self.image_placeholder_prefix} {filename}"
                       f"{self.image_placeholder_suffix}")

    def _process_latin_reference(self, groups: Tuple, prefix: str,
                                 image_placeholders: Dict) -> str:
        """Process Latin-based language image reference.

        Handles image references in languages using Latin alphabet such as:
        English, Spanish, French, German, Italian, Portuguese, etc.
        """
        if not groups:
            return ""

        if len(groups) == 1 and groups[0].isdigit():
            # Number format: Image 1, Imagen 1, Bild 1, etc.
            image_number = groups[0]
            safe_filename = self._find_image_by_number(image_number,
                                                     image_placeholders,
                                                     prefix)

            if safe_filename:
                return (f"{self.image_placeholder_prefix} {safe_filename}"
                       f"{self.image_placeholder_suffix}")
            else:
                return (f"{self.image_placeholder_prefix} {prefix}"
                       f"{image_number}{self.default_image_extension}"
                       f"{self.image_placeholder_suffix}")
        else:
            # Filename format: [image: filename], [imagen: filename], etc.
            filename = groups[0].strip()
            safe_filename = self._find_image_by_filename(filename,
                                                       image_placeholders)

            if safe_filename:
                return (f"{self.image_placeholder_prefix} {safe_filename}"
                       f"{self.image_placeholder_suffix}")
            else:
                return (f"{self.image_placeholder_prefix} {filename}"
                       f"{self.image_placeholder_suffix}")

    def _find_image_by_number(self, image_number: str,
                             image_placeholders: Dict, prefix: str) -> Optional[str]:
        """Find image by number in placeholders."""
        for placeholder, image_info in image_placeholders.items():
            filename = image_info.get('filename', '')
            if (f"{prefix}{image_number}" in filename or
                filename.startswith(f"{prefix}{image_number}")):
                safe_filename = image_info.get('safe_filename', 'unknown')
                logger.debug(f"Matched image {image_number} to {safe_filename}")
                return safe_filename
        return None

    def _find_image_by_filename(self, filename: str,
                               image_placeholders: Dict) -> Optional[str]:
        """Find image by filename in placeholders."""
        for placeholder, image_info in image_placeholders.items():
            info_filename = image_info.get('filename', '')
            if (filename in info_filename or info_filename in filename):
                safe_filename = image_info.get('safe_filename', 'unknown')
                logger.debug(f"Matched filename {filename} to {safe_filename}")
                return safe_filename
        return None

    def _find_image_positions(self, soup: BeautifulSoup,
                             image_placeholders: Dict) -> List[Dict]:
        """Find image positions in HTML content."""
        image_positions = []

        # First, try to find img tags (for cases where HTML still has img tags)
        images = soup.find_all('img')
        for img in images:
            image_info = self._process_html_image(img, image_placeholders)
            if image_info:
                position = self._calculate_image_position(img, soup)
                image_positions.append({
                    'placeholder': image_info.get('placeholder', ''),
                    'position': position,
                    'info': image_info
                })

        # If no img tags found, look for [IMAGE: ...] placeholders in text
        if not image_positions:
            # Use a simpler approach: extract text from HTML and find positions
            html_text = soup.get_text()
            for placeholder, image_info in image_placeholders.items():
                if placeholder in html_text:
                    # Find the position of the placeholder in the extracted text
                    position = html_text.find(placeholder)
                    if position != -1:
                        # Calculate the position in the original text content
                        # by finding the corresponding text before this position
                        text_before_placeholder = html_text[:position]
                        # Clean up the text to match the original text format
                        # Normalize whitespace and trim to control line length
                        text_before_placeholder = re.sub(
                            r'\s+', ' ', text_before_placeholder
                        ).strip()

                        image_positions.append({
                            'placeholder': placeholder,
                            'position': len(text_before_placeholder),
                            'info': image_info
                        })

        return sorted(image_positions, key=lambda x: x['position'])

    def _process_html_image(self, img, image_placeholders: Dict) -> Optional[Dict]:
        """Process HTML img element based on scenario type."""
        src = img.get('src', '')
        img_id = img.get('id', '')

        # Scenario 1: CID references
        if src.startswith(self.cid_protocol):
            cid = src[len(self.cid_protocol):]
            return self._find_by_cid(cid, image_placeholders)

        # Scenario 2: Direct filename references
        elif src.startswith(self.file_protocol):
            filename = self._extract_filename(src)
            return self._find_by_filename(filename, image_placeholders)

        # Scenario 3: ID-based references
        elif img_id:
            return self._find_by_id(img_id, image_placeholders)

        return None

    def _find_by_cid(self, cid: str, image_placeholders: Dict) -> Optional[Dict]:
        """Find image by Content-ID reference."""
        for placeholder, info in image_placeholders.items():
            if cid in info.get('filename', '') or info.get('filename', '') in cid:
                return info
        return None

    def _find_by_id(self, img_id: str, image_placeholders: Dict) -> Optional[Dict]:
        """Find image by img element id attribute."""
        for placeholder, info in image_placeholders.items():
            if img_id in info.get('filename', '') or info.get('filename', '') in img_id:
                return info
        return None

    def _extract_filename(self, src: str) -> str:
        """Extract filename from file:// URL."""
        return src.split('/')[-1] if '/' in src else src

    def _calculate_image_position(self, img_element, soup: BeautifulSoup) -> int:
        """Calculate text position for image insertion."""
        text_before = ''

        for element in soup.find_all():
            if element == img_element:
                break

            if element.name not in ['img', 'br', 'hr', 'script', 'style']:
                element_text = element.get_text()
                if element_text.strip():
                    text_before += element_text + ' '

        text_before = re.sub(r'\s+', ' ', text_before).strip()
        return len(text_before)

    def _insert_images_at_positions(self, text_content: str,
                                   image_positions: List[Dict]) -> str:
        """Insert images at calculated positions in text content."""
        if not image_positions:
            return text_content

        # Remove duplicates
        unique_images = {}
        for img_pos in image_positions:
            safe_filename = img_pos['info'].get('safe_filename', 'unknown')
            if safe_filename not in unique_images:
                unique_images[safe_filename] = img_pos

        unique_positions = list(unique_images.values())
        unique_positions.sort(key=lambda x: x['position'])

        lines = text_content.split('\n')
        result_lines = []

        for line in lines:
            result_lines.append(line)

            for img_pos in unique_positions:
                if (img_pos['position'] <= len('\n'.join(result_lines)) and
                    not img_pos.get('inserted', False)):
                    safe_filename = img_pos['info'].get('safe_filename', 'unknown')
                    result_lines.append(
                        f"{self.image_placeholder_prefix} {safe_filename}"
                        f"{self.image_placeholder_suffix}")
                    img_pos['inserted'] = True

        # Add remaining images at the end
        for img_pos in unique_positions:
            if not img_pos.get('inserted', False):
                safe_filename = img_pos['info'].get('safe_filename', 'unknown')
                result_lines.append(
                    f"{self.image_placeholder_prefix} {safe_filename}"
                    f"{self.image_placeholder_suffix}")

        return '\n'.join(result_lines)

    def _check_positioned_images(self, content: str,
                                image_placeholders: Dict) -> set:
        """Check which images have been positioned in content."""
        positioned_images = set()

        for placeholder, info in image_placeholders.items():
            safe_filename = info.get('safe_filename',
                                   info.get('filename', 'unknown'))
            image_placeholder = (f"{self.image_placeholder_prefix} "
                               f"{safe_filename}{self.image_placeholder_suffix}")

            if image_placeholder in content:
                positioned_images.add(placeholder)

        return positioned_images

    def _get_remaining_images(self, image_placeholders: Dict,
                             positioned_images: set) -> Dict:
        """Get images that haven't been positioned yet."""
        return {k: v for k, v in image_placeholders.items()
                if k not in positioned_images}

    def _process_custom_patterns(self, content: str,
                                remaining_images: Dict) -> str:
        """Process remaining images using custom patterns."""
        for placeholder, info in remaining_images.items():
            original_filename = info.get('filename', '')
            safe_filename = info.get('safe_filename',
                                   info.get('filename', 'unknown'))

            if original_filename:
                base_name = original_filename.rsplit('.', 1)[0]
                custom_patterns = self._generate_custom_patterns(base_name)

                for pattern in custom_patterns:
                    try:
                        if re.search(pattern, content):
                            image_placeholder = (
                                f"{self.image_placeholder_prefix} "
                                f"{safe_filename}{self.image_placeholder_suffix}")
                            content = re.sub(pattern, image_placeholder, content)
                            break
                    except re.error as e:
                        logger.debug(f"Invalid regex pattern '{pattern}': {e}")
                        continue

        return content

    def _generate_custom_patterns(self, base_name: str) -> List[str]:
        """Generate custom patterns based on filename."""
        patterns = []

        # Number-based patterns
        if base_name.isdigit() or any(char.isdigit() for char in base_name):
            number_match = re.search(r'(\d+)', base_name)
            if number_match:
                number = number_match.group(1)

                # Chinese patterns
                patterns.extend([
                    rf"图片{number}\s*（可在附件中查看）",
                    rf"图片{number}\s*\(可在附件中查看\)",
                    rf"图片{number}\s*（见附件）",
                    rf"图片{number}\s*\(见附件\)",
                    rf"图片{number}\s*（附件）",
                    rf"图片{number}\s*\(附件\)",
                ])

                # Latin-based language patterns
                patterns.extend([
                    # English
                    rf"[Ii]mage\s*{number}\s*see\s+attached",
                    rf"[Ii]mage\s*{number}\s*attached\s+image",
                    rf"[Ii]mage\s*{number}\s*image\s+attached",
                    # Spanish
                    rf"[Ii]magen\s*{number}\s*ver\s+adjunto",
                    rf"[Ii]magen\s*{number}\s*imagen\s+adjunta",
                    # German
                    rf"[Bb]ild\s*{number}\s*siehe\s+anhäng",
                    rf"[Bb]ild\s*{number}\s*anhäng\s+bild",
                    # French
                    rf"[Ii]mage\s*{number}\s*voir\s+pièce\s+jointe",
                    rf"[Ii]mage\s*{number}\s*image\s+jointe",
                ])

        # Filename-based patterns
        patterns.extend([
            # Chinese
            rf"\[图片:\s*{re.escape(base_name)}\]",
            rf"{re.escape(base_name)}\s*（可在附件中查看）",
            rf"{re.escape(base_name)}\s*\(可在附件中查看\)",
            # Latin-based languages
            rf"\[[Ii]mage:\s*{re.escape(base_name)}\]",
            rf"\[[Ii]magen:\s*{re.escape(base_name)}\]",
            rf"\[[Bb]ild:\s*{re.escape(base_name)}\]",
            rf"\[[Ii]magine:\s*{re.escape(base_name)}\]",
        ])

        return patterns

    def _append_remaining_images(self, content: str,
                                image_placeholders: Dict,
                                positioned_images: set) -> str:
        """Append remaining images at the end of content."""
        positioned_safe_filenames = set()
        for placeholder in positioned_images:
            info = image_placeholders[placeholder]
            safe_filename = info.get('safe_filename',
                                   info.get('filename', 'unknown'))
            positioned_safe_filenames.add(safe_filename)

        all_safe_filenames = {info.get('safe_filename',
                                     info.get('filename', 'unknown'))
                             for info in image_placeholders.values()}
        remaining_safe_filenames = (all_safe_filenames -
                                   positioned_safe_filenames)

        if remaining_safe_filenames:
            lines = content.split('\n')
            lines.append("")  # Add blank line

            for safe_filename in remaining_safe_filenames:
                lines.append(f"{self.image_placeholder_prefix} "
                           f"{safe_filename}{self.image_placeholder_suffix}")

            content = '\n'.join(lines)
            logger.info(f"Appended {len(remaining_safe_filenames)} "
                       f"remaining images at end")

        return content


# Convenience function for backward compatibility
def process_email_images(text_content: str,
                         html_content: str,
                         image_placeholders: Dict) -> str:
    """
    Convenience function for processing email images.

    This function provides a simple interface for processing email images
    using the EmailImageProcessor class.

    Args:
        text_content: Plain text content to embed images into
        html_content: HTML content for position calculation
        image_placeholders: Dictionary of image information

    Returns:
        str: Text content with embedded image references at appropriate
            positions
    """
    processor = EmailImageProcessor()
    return processor.process_images(
        text_content, html_content, image_placeholders)
