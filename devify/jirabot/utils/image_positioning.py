"""
Image positioning algorithm for email content.
"""

import re
from bs4 import BeautifulSoup


def embed_images_in_text_with_html_positioning(
    text_content: str,
    html_content: str,
    image_placeholders: dict
) -> str:
    """
    Embed image references in text content at positions
    corresponding to HTML structure.
    """
    if not html_content or not image_placeholders:
        return simple_append_images(
            text_content,
            image_placeholders
        )

    try:
        # Parse HTML
        soup = BeautifulSoup(html_content, 'html.parser')

        # Find image positions in HTML
        image_positions = find_image_positions_in_html(soup, image_placeholders)

        if not image_positions:
            return simple_append_images(text_content, image_placeholders)

        # Insert images at corresponding positions in text
        return insert_images_at_positions(text_content, image_positions)

    except Exception as e:
        print(f"Failed to parse HTML for image positioning: {e}")
        return simple_append_images(text_content, image_placeholders)


def find_image_positions_in_html(soup, image_placeholders: dict):
    """
    Find positions of images in HTML content.
    """
    image_positions = []

    # Find all images
    images = soup.find_all('img')

    for img in images:
        src = img.get('src', '')
        if src.startswith('cid:'):
            cid = src[4:]  # Remove 'cid:' prefix

            # Find corresponding image placeholder
            for placeholder, info in image_placeholders.items():
                if cid in info['filename'] or info['filename'] in cid:
                    # Calculate position based on text before this image
                    position = calculate_image_position(img, soup)
                    image_positions.append({
                        'placeholder': placeholder,
                        'position': position,
                        'info': info
                    })
                    break

    return sorted(image_positions, key=lambda x: x['position'])


def calculate_image_position(img_element, soup):
    """
    Calculate the position of an image in the text flow.
    """
    # Get all text before this image
    text_before = ''
    for element in soup.find_all():
        if element == img_element:
            break
        if element.name not in ['img', 'br', 'hr']:
            text_before += element.get_text() + ' '

    # Clean up the text
    text_before = re.sub(r'\s+', ' ', text_before).strip()
    return len(text_before)


def insert_images_at_positions(text_content: str, image_positions: list) -> str:
    """
    Insert image references at calculated positions in text.
    """
    if not image_positions:
        return text_content

    # Split text into words for better positioning
    words = text_content.split()
    result_words = []
    current_pos = 0

    for word in words:
        result_words.append(word)
        current_pos += len(word) + 1  # +1 for space

        # Check if any image should be inserted here
        for img_pos in image_positions:
            if (img_pos['position'] <= current_pos and
                not img_pos.get('inserted', False)):
                # Insert image reference
                result_words.append(f"[{img_pos['placeholder']}]")
                img_pos['inserted'] = True

    # Add any remaining images at the end
    for img_pos in image_positions:
        if not img_pos.get('inserted', False):
            result_words.append(f"[{img_pos['placeholder']}]")

    return ' '.join(result_words)


def simple_append_images(text_content: str, image_placeholders: dict) -> str:
    """
    Simple fallback: append images at the end.
    """
    lines = text_content.split('\n')

    if image_placeholders:
        lines.append("\n--- Images ---")
        for placeholder, info in image_placeholders.items():
            lines.append(f"{placeholder}")

    return '\n'.join(lines)
