"""
Unit tests for EmailFlankerParser image filtering functionality.

This module tests the image filtering capabilities using mocks to isolate
the logic from external dependencies (PIL, file I/O, etc.).

Testing strategy:
- Focus on individual functions with mocked inputs/outputs
- Test normal and abnormal cases
- Use mocks to simulate various scenarios without creating real files
"""

import pytest
from unittest.mock import patch, MagicMock

from devify.threadline.utils.email.parsers.enhanced import EmailFlankerParser


@pytest.fixture
def parser(tmp_path):
    """Create EmailFlankerParser instance for testing."""
    attachment_dir = tmp_path / "attachments"
    attachment_dir.mkdir()
    return EmailFlankerParser(str(attachment_dir))


@pytest.mark.unit
class TestImageValidation:
    """Test image validation functionality using mocks."""

    def test_validate_image_too_small_size(self, parser):
        """Test that images smaller than MIN_IMAGE_ATTACHMENT_SIZE are rejected."""
        small_payload = b"x" * (parser.MIN_IMAGE_ATTACHMENT_SIZE - 1)

        is_valid, reason = parser._validate_image_attachment(
            small_payload, "small_image.png"
        )

        assert not is_valid
        assert "file size too small" in reason
        assert str(len(small_payload)) in reason

    def test_validate_image_zero_dimensions(self, parser):
        """Test that images with zero dimensions are rejected."""
        large_payload = b"x" * (parser.MIN_IMAGE_ATTACHMENT_SIZE + 1000)

        mock_image = MagicMock()
        mock_image.__enter__ = lambda self: self
        mock_image.__exit__ = lambda *args: None

        # Test zero width
        mock_image.size = (0, 100)
        with patch('devify.threadline.utils.email.parsers.enhanced.Image.open', return_value=mock_image):
            is_valid, reason = parser._validate_image_attachment(
                large_payload, "zero_width.jpg"
            )
            assert not is_valid
            assert "invalid dimensions" in reason

        # Test zero height
        mock_image.size = (100, 0)
        with patch('devify.threadline.utils.email.parsers.enhanced.Image.open', return_value=mock_image):
            is_valid, reason = parser._validate_image_attachment(
                large_payload, "zero_height.jpg"
            )
            assert not is_valid
            assert "invalid dimensions" in reason

    def test_validate_image_too_small_dimensions(self, parser):
        """Test that images with dimensions smaller than minimum are rejected."""
        large_payload = b"x" * (parser.MIN_IMAGE_ATTACHMENT_SIZE + 1000)

        mock_image = MagicMock()
        mock_image.size = (30, 30)
        mock_image.__enter__ = lambda self: self
        mock_image.__exit__ = lambda *args: None

        with patch('devify.threadline.utils.email.parsers.enhanced.Image.open', return_value=mock_image):
            is_valid, reason = parser._validate_image_attachment(
                large_payload, "small_dim.jpg"
            )

            assert not is_valid
            assert "dimensions too small" in reason
            assert "30x30" in reason

    def test_validate_image_extreme_aspect_ratio_wide(self, parser):
        """Test that very wide images (extreme aspect ratio) are rejected."""
        large_payload = b"x" * (parser.MIN_IMAGE_ATTACHMENT_SIZE + 1000)

        mock_image = MagicMock()
        mock_image.size = (600, 50)
        mock_image.__enter__ = lambda self: self
        mock_image.__exit__ = lambda *args: None

        with patch('devify.threadline.utils.email.parsers.enhanced.Image.open', return_value=mock_image):
            is_valid, reason = parser._validate_image_attachment(
                large_payload, "wide_image.jpg"
            )

            assert not is_valid
            assert "aspect ratio too extreme" in reason

    def test_validate_image_extreme_aspect_ratio_tall(self, parser):
        """Test that very tall images (extreme aspect ratio) are rejected."""
        large_payload = b"x" * (parser.MIN_IMAGE_ATTACHMENT_SIZE + 1000)

        mock_image = MagicMock()
        mock_image.size = (50, 600)
        mock_image.__enter__ = lambda self: self
        mock_image.__exit__ = lambda *args: None

        with patch('devify.threadline.utils.email.parsers.enhanced.Image.open', return_value=mock_image):
            is_valid, reason = parser._validate_image_attachment(
                large_payload, "tall_image.jpg"
            )

            assert not is_valid
            assert "aspect ratio too extreme" in reason

    def test_validate_image_borderline_aspect_ratio_passes(self, parser):
        """Test that images with aspect ratio exactly at max (10:1) pass."""
        large_payload = b"x" * (parser.MIN_IMAGE_ATTACHMENT_SIZE + 1000)

        mock_image = MagicMock()
        mock_image.size = (500, 50)
        mock_image.__enter__ = lambda self: self
        mock_image.__exit__ = lambda *args: None

        with patch('devify.threadline.utils.email.parsers.enhanced.Image.open', return_value=mock_image):
            is_valid, reason = parser._validate_image_attachment(
                large_payload, "max_aspect_image.jpg"
            )

            assert is_valid, f"Image should be valid but got reason: {reason}"
            assert reason == ""

    def test_validate_image_borderline_aspect_ratio_fails(self, parser):
        """Test that images with aspect ratio over max (10.02:1) fail."""
        large_payload = b"x" * (parser.MIN_IMAGE_ATTACHMENT_SIZE + 1000)

        mock_image = MagicMock()
        mock_image.size = (501, 50)
        mock_image.__enter__ = lambda self: self
        mock_image.__exit__ = lambda *args: None

        with patch('devify.threadline.utils.email.parsers.enhanced.Image.open', return_value=mock_image):
            is_valid, reason = parser._validate_image_attachment(
                large_payload, "over_max_aspect_image.jpg"
            )

            assert not is_valid
            assert "aspect ratio too extreme" in reason

    def test_validate_image_valid(self, parser):
        """Test that valid images pass all validation checks."""
        mock_image = MagicMock()
        mock_image.__enter__ = lambda self: self
        mock_image.__exit__ = lambda *args: None

        # Test with exact minimum size and dimensions
        exact_size_payload = b"x" * parser.MIN_IMAGE_ATTACHMENT_SIZE
        mock_image.size = (50, 50)
        with patch('devify.threadline.utils.email.parsers.enhanced.Image.open', return_value=mock_image):
            is_valid, reason = parser._validate_image_attachment(
                exact_size_payload, "min_size_dim.jpg"
            )
            assert is_valid, f"Image should be valid but got reason: {reason}"
            assert reason == ""

        # Test with larger size and dimensions
        large_payload = b"x" * (parser.MIN_IMAGE_ATTACHMENT_SIZE + 1000)
        mock_image.size = (200, 200)
        with patch('devify.threadline.utils.email.parsers.enhanced.Image.open', return_value=mock_image):
            is_valid, reason = parser._validate_image_attachment(
                large_payload, "valid_image.jpg"
            )
            assert is_valid, f"Image should be valid but got reason: {reason}"
            assert reason == ""

    def test_validate_image_unreadable_format(self, parser):
        """Test that unreadable image formats are handled gracefully."""
        large_payload = b"This is not an image file" * 1000

        with patch('devify.threadline.utils.email.parsers.enhanced.Image.open', side_effect=Exception("Cannot read image")):
            is_valid, reason = parser._validate_image_attachment(
                large_payload, "invalid.txt"
            )

            assert is_valid, "Unreadable images should be considered valid (might be valid in unsupported format)"
            assert reason == ""


@pytest.mark.unit
class TestInvalidImagePlaceholderCleanup:
    """Test invalid image placeholder cleanup functionality."""

    def test_clean_invalid_placeholders_removes_filtered_images(self, parser):
        """Test that placeholders for filtered images are removed."""
        text_content = (
            "This is a test email.\n"
            "[IMAGE: filtered_image1.png]\n"
            "Some text in between.\n"
            "[IMAGE: filtered_image2.jpg]\n"
            "End of email."
        )

        attachments = [
            {
                'is_image': True,
                'safe_filename': 'valid_image.png',
                'filename': 'valid_image.png'
            }
        ]

        cleaned = parser._clean_invalid_image_placeholders(
            text_content, attachments
        )

        assert "[IMAGE: filtered_image1.png]" not in cleaned
        assert "[IMAGE: filtered_image2.jpg]" not in cleaned
        assert "This is a test email" in cleaned
        assert "Some text in between" in cleaned
        assert "End of email" in cleaned

    def test_clean_invalid_placeholders_preserves_valid_images(self, parser):
        """Test that placeholders for valid images are preserved."""
        text_content = (
            "This is a test email.\n"
            "[IMAGE: valid_image1.png]\n"
            "Some text in between.\n"
            "[IMAGE: valid_image2.jpg]\n"
            "End of email."
        )

        attachments = [
            {
                'is_image': True,
                'safe_filename': 'valid_image1.png',
                'filename': 'valid_image1.png'
            },
            {
                'is_image': True,
                'safe_filename': 'valid_image2.jpg',
                'filename': 'valid_image2.jpg'
            }
        ]

        cleaned = parser._clean_invalid_image_placeholders(
            text_content, attachments
        )

        assert "[IMAGE: valid_image1.png]" in cleaned
        assert "[IMAGE: valid_image2.jpg]" in cleaned
        assert "This is a test email" in cleaned
        assert "Some text in between" in cleaned
        assert "End of email" in cleaned

    def test_clean_invalid_placeholders_handles_mixed(self, parser):
        """Test cleanup with mix of valid and invalid placeholders."""
        text_content = (
            "Email content.\n"
            "[IMAGE: valid1.png]\n"
            "More text.\n"
            "[IMAGE: invalid1.jpg]\n"
            "[IMAGE: valid2.png]\n"
            "[IMAGE: invalid2.gif]\n"
            "End."
        )

        attachments = [
            {
                'is_image': True,
                'safe_filename': 'valid1.png',
                'filename': 'valid1.png'
            },
            {
                'is_image': True,
                'safe_filename': 'valid2.png',
                'filename': 'valid2.png'
            }
        ]

        cleaned = parser._clean_invalid_image_placeholders(
            text_content, attachments
        )

        assert "[IMAGE: valid1.png]" in cleaned
        assert "[IMAGE: valid2.png]" in cleaned
        assert "[IMAGE: invalid1.jpg]" not in cleaned
        assert "[IMAGE: invalid2.gif]" not in cleaned
        assert "Email content" in cleaned
        assert "More text" in cleaned
        assert "End" in cleaned

    def test_clean_invalid_placeholders_early_returns(self, parser):
        """Test cleanup early return cases (no placeholders, empty text, etc.)."""
        # Test empty text
        cleaned = parser._clean_invalid_image_placeholders("", [])
        assert cleaned == ""

        # Test text without [IMAGE: marker
        text_content = "This is a plain text email without images."
        cleaned = parser._clean_invalid_image_placeholders(text_content, [])
        assert cleaned == text_content

        # Test text with [IMAGE: but no valid placeholders
        text_content = "This email has [IMAGE: but incomplete placeholder."
        cleaned = parser._clean_invalid_image_placeholders(
            text_content,
            [{'is_image': True, 'safe_filename': 'image1.png', 'filename': 'image1.png'}]
        )
        assert cleaned == text_content

    def test_clean_invalid_placeholders_handles_empty_attachments(self, parser):
        """Test cleanup when attachments list is empty."""
        text_content = (
            "Email with images.\n"
            "[IMAGE: image1.png]\n"
            "[IMAGE: image2.jpg]\n"
        )
        attachments = []

        cleaned = parser._clean_invalid_image_placeholders(
            text_content, attachments
        )

        assert "[IMAGE: image1.png]" not in cleaned
        assert "[IMAGE: image2.jpg]" not in cleaned
        assert "Email with images" in cleaned

    def test_clean_invalid_placeholders_ignores_non_image_attachments(self, parser):
        """Test that non-image attachments don't affect placeholder cleanup."""
        text_content = (
            "Email content.\n"
            "[IMAGE: image1.png]\n"
            "[IMAGE: document.pdf]\n"
        )

        attachments = [
            {
                'is_image': False,
                'safe_filename': 'document.pdf',
                'filename': 'document.pdf'
            }
        ]

        cleaned = parser._clean_invalid_image_placeholders(
            text_content, attachments
        )

        assert "[IMAGE: image1.png]" not in cleaned
        assert "[IMAGE: document.pdf]" not in cleaned


@pytest.mark.unit
class TestImageFilteringConstants:
    """Test image filtering constants."""

    def test_parser_constants(self, parser):
        """Test that parser has correct filtering constants."""
        assert parser.MIN_IMAGE_ATTACHMENT_SIZE == 10 * 1024
        assert parser.MIN_IMAGE_WIDTH == 50
        assert parser.MIN_IMAGE_HEIGHT == 50
        assert parser.MAX_IMAGE_ASPECT_RATIO == 10
