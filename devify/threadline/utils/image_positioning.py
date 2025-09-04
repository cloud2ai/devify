"""
Image positioning algorithm for email content.

This module provides functionality to intelligently position image references
within text content based on HTML structure. It supports both Chinese and
English image descriptions and various image reference formats.
"""

import logging
import re
from typing import Dict, List, Optional

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def embed_images_with_html(
    text_content: str,
    html_content: str,
    image_placeholders: dict
) -> str:
    """
    Embed image references in text content at positions corresponding to
    HTML structure.

    This function intelligently positions images based on HTML structure
    to maintain the visual flow of the original content. If HTML parsing
    fails, it falls back to appending images at the end.

    Args:
        text_content: Plain text content to embed images into
        html_content: HTML content for position calculation
        image_placeholders: Dictionary of image information with
                          placeholders as keys

    Returns:
        str: Text content with embedded image references at appropriate
             positions

    Example:
        Input:
            text_content: "Hello world"
            html_content: "<p>Hello <img src='cid:image1.jpg'> world</p>"
            image_placeholders: {"[IMAGE: img1.jpg]": {...}}
        Output: "Hello\n[IMAGE: img1.jpg]\nworld"
    """
    if not html_content or not image_placeholders:
        logger.debug("No HTML content or image placeholders, using fallback")
        return append_images(text_content, image_placeholders)

    try:
        logger.info(
            f"Processing {len(image_placeholders)} images with HTML positioning"
        )

        # Parse HTML content
        soup = BeautifulSoup(html_content, 'html.parser')
        logger.debug("HTML parsed successfully")

        # Normalize image references in HTML content
        normalized_html_content = normalize_refs(
            html_content,
            image_placeholders
        )
        logger.debug("Image references normalized")

        # Find image positions in HTML structure
        image_positions = find_positions(soup, image_placeholders)
        logger.debug(f"Found {len(image_positions)} image positions")

        if not image_positions:
            logger.info("No image positions found, using fallback")
            return append_images(text_content, image_placeholders)

        # Insert images at calculated positions in text
        result = insert_at_positions(text_content, image_positions)
        logger.info(
            "Images embedded successfully with HTML positioning"
        )
        return result

    except Exception as e:
        logger.error(
            f"Failed to parse HTML for image positioning: {e}"
        )
        logger.info("Falling back to simple image append")
        return append_images(text_content, image_placeholders)


def normalize_refs(
    html_content: str,
    image_placeholders: dict
) -> str:
    """
    Normalize image references in HTML content to standard format.

    Converts various image reference formats to [IMAGE: safe_filename] format.
    Supports both Chinese and English descriptions with intelligent matching.

    Args:
        html_content: Raw HTML content containing image references
        image_placeholders: Dictionary of image information for matching

    Returns:
        str: HTML content with normalized image references

    Example:
        Input: "图片1（可在附件中查看）"
        Output: "[IMAGE: safe_filename.jpg]"
    """
    if not image_placeholders:
        logger.debug("No image placeholders to normalize")
        return html_content

    logger.debug(
        f"Normalizing image references for {len(image_placeholders)} images"
    )
    result_html = html_content

    # Enhanced patterns to match both Chinese and English image references
    chinese_patterns = [
        r'\[图片:\s*([^\]\(]+)\([^\)]*\)\]',  # [图片: filename(description)]
        r'\[图片:\s*([^\]]+)\]',  # [图片: filename]
        r'图片(\d+)\s*（可在附件中查看）',  # 图片1（可在附件中查看）
        r'图片(\d+)\s*\(可在附件中查看\)',  # 图片1(可在附件中查看)
    ]

    english_patterns = [
        r'\[image:\s*([^\]\(]+)\([^\)]*\)\]',  # [image: filename(description)]
        r'\[image:\s*([^\]]+)\]',  # [image: filename]
        r'Image\s*(\d+)\s*\([^\)]*\)',  # Image 1(description)
        r'Image\s*(\d+)',  # Image 1
    ]

    # Process Chinese image references
    for pattern in chinese_patterns:
        def replace_chinese_image(match):
            if '图片' in pattern:
                # Handle 图片1（可在附件中查看） format
                if ('（可在附件中查看）' in pattern or
                    '(可在附件中查看)' in pattern):
                    image_number = match.group(1)
                    logger.debug(
                        f"Processing Chinese image number: {image_number}"
                    )

                    # Try to find matching image in placeholders
                    for placeholder, image_info in image_placeholders.items():
                        if (f"图片{image_number}" in
                            image_info.get('filename', '') or
                            image_info.get('filename', '').startswith(
                                f"图片{image_number}")):
                            safe_filename = image_info.get(
                                'safe_filename', 'unknown'
                            )
                            logger.debug(
                                f"Matched image {image_number} to {safe_filename}"
                            )
                            return f"[IMAGE: {safe_filename}]"

                    # Fallback: use image number as filename
                    logger.debug(
                        f"No match found for image {image_number}, using fallback"
                    )
                    return f"[IMAGE: 图片{image_number}.jpg]"
                else:
                    # Handle [图片: filename] format
                    filename = match.group(1).strip()
                    logger.debug(f"Processing Chinese filename: {filename}")

                    # Try to find matching image in placeholders
                    for placeholder, image_info in image_placeholders.items():
                        if (filename in image_info.get('filename', '') or
                            image_info.get('filename', '') in filename):
                            safe_filename = image_info.get(
                                'safe_filename', 'unknown'
                            )
                            logger.debug(
                                f"Matched filename {filename} to {safe_filename}"
                            )
                            return f"[IMAGE: {safe_filename}]"

                    # Fallback: use original filename
                    logger.debug(
                        f"No match found for filename {filename}, using fallback"
                    )
                    return f"[IMAGE: {filename}]"
            return match.group(0)

        result_html = re.sub(pattern, replace_chinese_image, result_html)

    # Process English image references
    for pattern in english_patterns:
        def replace_english_image(match):
            if 'Image' in pattern:
                # Handle Image 1 format
                if '([^)]*)' in pattern:
                    image_number = match.group(1)
                    logger.debug(
                        f"Processing English image number: {image_number}"
                    )

                    # Try to find matching image in placeholders
                    for placeholder, image_info in image_placeholders.items():
                        if (f"image{image_number}" in
                            image_info.get('filename', '').lower() or
                            image_info.get('filename', '').lower().startswith(
                                f"image{image_number}")):
                            safe_filename = image_info.get(
                                'safe_filename', 'unknown'
                            )
                            logger.debug(
                                f"Matched image {image_number} to {safe_filename}"
                            )
                            return f"[IMAGE: {safe_filename}]"

                    # Fallback: use image number as filename
                    logger.debug(
                        f"No match found for image {image_number}, using fallback"
                    )
                    return f"[IMAGE: image{image_number}.jpg]"
                else:
                    # Handle [image: filename] format
                    filename = match.group(1).strip()
                    logger.debug(f"Processing English filename: {filename}")

                    # Try to find matching image in placeholders
                    for placeholder, image_info in image_placeholders.items():
                        if (filename.lower() in
                            image_info.get('filename', '').lower() or
                            image_info.get('filename', '').lower() in
                            filename.lower()):
                            safe_filename = image_info.get(
                                'safe_filename', 'unknown'
                            )
                            logger.debug(
                                f"Matched filename {filename} to {safe_filename}"
                            )
                            return f"[IMAGE: {safe_filename}]"

                    # Fallback: use original filename
                    logger.debug(
                        f"No match found for filename {filename}, using fallback"
                    )
                    return f"[IMAGE: {filename}]"
            return match.group(0)

        result_html = re.sub(
            pattern,
            replace_english_image,
            result_html,
            flags=re.IGNORECASE
        )

    logger.info("Image references normalized successfully")
    return result_html


def find_positions(soup: BeautifulSoup, image_placeholders: dict) -> List[Dict]:
    """
    Find positions of images in HTML content for accurate text positioning.

    Analyzes HTML structure to determine where images should be positioned
    in the corresponding text content. Supports multiple image source formats.

    Args:
        soup: BeautifulSoup object of parsed HTML
        image_placeholders: Dictionary of image information

    Returns:
        List[Dict]: List of image position information sorted by position

    Example:
        Returns: [
            {
                'placeholder': '[IMAGE: img1.jpg]',
                'position': 15,
                'info': {...}
            }
        ]
    """
    image_positions = []
    logger.debug("Finding image positions in HTML content")

    # Find all image elements in HTML
    images = soup.find_all('img')
    logger.debug(f"Found {len(images)} image elements")

    for img in images:
        src = img.get('src', '')
        img_id = img.get('id', '')
        logger.debug(f"Processing image: src='{src}', id='{img_id}'")

        # Handle different image source formats
        image_info = None

        # Case 1: cid: protocol (inline email images)
        if src.startswith('cid:'):
            cid = src[4:]  # Remove 'cid:' prefix
            logger.debug(f"Processing cid: {cid}")
            image_info = find_by_cid(cid, image_placeholders)

        # Case 2: file:// protocol (local file references)
        elif src.startswith('file://'):
            filename = extract_filename(src)
            logger.debug(f"Processing file:// {filename}")
            image_info = find_by_filename(filename, image_placeholders)

        # Case 3: Try to match by img id attribute
        elif img_id:
            logger.debug(f"Processing img id: {img_id}")
            image_info = find_by_id(img_id, image_placeholders)

        if image_info:
            # Calculate position based on text before this image
            position = calc_position(img, soup)
            logger.debug(f"Image positioned at text position {position}")

            image_positions.append({
                'placeholder': image_info.get('placeholder', ''),
                'position': position,
                'info': image_info
            })
        else:
            logger.warning(
                f"No matching image info found for: src='{src}', id='{img_id}'"
            )

    # Sort by position for proper insertion order
    sorted_positions = sorted(image_positions, key=lambda x: x['position'])
    logger.info(f"Found {len(sorted_positions)} image positions")
    return sorted_positions


def find_by_cid(cid: str, image_placeholders: dict) -> Optional[Dict]:
    """
    Find image by Content-ID (cid:) reference.

    Args:
        cid: Content-ID string from img src attribute
        image_placeholders: Dictionary of image information

    Returns:
        Optional[Dict]: Image information if found, None otherwise
    """
    logger.debug(f"Searching for image with cid: {cid}")

    for placeholder, info in image_placeholders.items():
        if cid in info.get('filename', '') or info.get('filename', '') in cid:
            logger.debug(
                f"Found image by cid: {cid} -> {info.get('filename', 'unknown')}"
            )
            return info

    logger.debug(f"No image found for cid: {cid}")
    return None


def find_by_filename(filename: str, image_placeholders: dict) -> Optional[Dict]:
    """
    Find image by filename reference.

    Args:
        filename: Filename to search for
        image_placeholders: Dictionary of image information

    Returns:
        Optional[Dict]: Image information if found, None otherwise
    """
    logger.debug(f"Searching for image with filename: {filename}")

    for placeholder, info in image_placeholders.items():
        if (filename in info.get('filename', '') or
            info.get('filename', '') in filename):
            logger.debug(
                f"Found image by filename: {filename} -> "
                f"{info.get('filename', 'unknown')}"
            )
            return info

    logger.debug(f"No image found for filename: {filename}")
    return None


def find_by_id(img_id: str, image_placeholders: dict) -> Optional[Dict]:
    """
    Find image by img element id attribute.

    Args:
        img_id: ID attribute value from img element
        image_placeholders: Dictionary of image information

    Returns:
        Optional[Dict]: Image information if found, None otherwise
    """
    logger.debug(f"Searching for image with id: {img_id}")

    for placeholder, info in image_placeholders.items():
        # Try to match by various identifiers
        if (img_id in info.get('filename', '') or
            info.get('filename', '') in img_id or
            img_id in info.get('safe_filename', '') or
            info.get('safe_filename', '') in img_id):
            logger.debug(
                f"Found image by id: {img_id} -> {info.get('filename', 'unknown')}"
            )
            return info

    logger.debug(f"No image found for id: {img_id}")
    return None


def extract_filename(file_path: str) -> str:
    """
    Extract filename from file:// path.

    Args:
        file_path: File path starting with file://

    Returns:
        str: Extracted filename without path

    Example:
        Input: "file:///path/to/image.jpg"
        Output: "image.jpg"
    """
    # Remove file:// prefix and get the filename
    if file_path.startswith('file://'):
        file_path = file_path[7:]

    # Split by '/' and get the last part (filename)
    parts = file_path.split('/')
    if parts:
        filename = parts[-1]
        logger.debug(
            f"Extracted filename: {filename} from path: {file_path}"
        )
        return filename

    logger.debug(f"Could not extract filename from path: {file_path}")
    return file_path


def calc_position(img_element, soup: BeautifulSoup) -> int:
    """
    Calculate the position of an image in the text flow.

    Improved algorithm to handle nested elements better by walking through
    all elements in document order and calculating text position.

    Args:
        img_element: BeautifulSoup img element
        soup: BeautifulSoup object of the entire HTML

    Returns:
        int: Character position where image should be inserted
    """
    logger.debug("Calculating image position in text flow")

    # Get all text before this image
    text_before = ''

    # Walk through all elements in document order
    for element in soup.find_all():
        if element == img_element:
            break

        # Skip certain elements that don't contribute to text flow
        if element.name not in ['img', 'br', 'hr', 'script', 'style']:
            element_text = element.get_text()
            if element_text.strip():
                text_before += element_text + ' '

    # Clean up the text and calculate position
    text_before = re.sub(r'\s+', ' ', text_before).strip()
    position = len(text_before)

    logger.debug(f"Image position calculated: {position} characters")
    return position


def insert_at_positions(text_content: str, image_positions: List[Dict]) -> str:
    """
    Insert image references at calculated positions in text content.

    Improved algorithm for better positioning that maintains text flow
    and ensures images are inserted at appropriate locations.

    Args:
        text_content: Original text content
        image_positions: List of image position information

    Returns:
        str: Text content with images inserted at calculated positions

    Example:
        Input:
            text_content: "Hello world"
            image_positions: [{'position': 5, 'info': {'safe_filename': 'img1.jpg'}}]
        Output: "Hello\n[IMAGE: img1.jpg]\nworld"
    """
    if not image_positions:
        logger.debug("No image positions to insert")
        return text_content

    logger.debug(
        f"Inserting {len(image_positions)} images at calculated positions"
    )

    # Split text into lines for better positioning
    lines = text_content.split('\n')
    result_lines = []

    for line in lines:
        result_lines.append(line)

        # Check if any image should be inserted after this line
        for img_pos in image_positions:
            if (img_pos['position'] <= len('\n'.join(result_lines)) and
                not img_pos.get('inserted', False)):
                # Insert image reference on a new line
                safe_filename = img_pos['info'].get('safe_filename', 'unknown')
                result_lines.append(f"[IMAGE: {safe_filename}]")
                img_pos['inserted'] = True
                logger.debug(f"Inserted image {safe_filename} after line")

    # Add any remaining images at the end
    for img_pos in image_positions:
        if not img_pos.get('inserted', False):
            safe_filename = img_pos['info'].get('safe_filename', 'unknown')
            result_lines.append(f"[IMAGE: {safe_filename}]")
            logger.debug(f"Inserted remaining image {safe_filename} at end")

    result = '\n'.join(result_lines)
    logger.info("Images inserted successfully at calculated positions")
    return result


def append_images(text_content: str, image_placeholders: dict) -> str:
    """
    Simple fallback method: append all images at the end of text.

    This method is used when HTML positioning fails or when no HTML
    content is available. It ensures all images are included in the
    final output.

    Args:
        text_content: Original text content
        image_placeholders: Dictionary of image information

    Returns:
        str: Text content with images appended at the end

    Example:
        Input:
            text_content: "Hello world"
            image_placeholders: {"[IMAGE: img1.jpg]": {...}}
        Output: "Hello world\n\n--- Images ---\n[IMAGE: img1.jpg]"
    """
    lines = text_content.split('\n')

    if image_placeholders:
        logger.debug(f"Appending {len(image_placeholders)} images at end")
        lines.append("\n--- Images ---")

        for placeholder, info in image_placeholders.items():
            # Always use safe_filename for consistency
            safe_filename = info.get('safe_filename', info.get('filename', 'unknown'))
            lines.append(f"[IMAGE: {safe_filename}]")
            logger.debug(f"Appended image: {safe_filename}")

        logger.info("Images appended successfully at end of text")
    else:
        logger.debug("No images to append")

    return '\n'.join(lines)
