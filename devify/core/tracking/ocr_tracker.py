import logging
from typing import Dict, Optional

from django.conf import settings
from django.utils import timezone

from devtoolbox.ocr import OCRService
from devtoolbox.ocr.azure_provider import AzureOCRConfig

logger = logging.getLogger(__name__)


class OCRTracker:
    """
    Business-level OCR API call tracker for billing and monitoring

    This service wraps OCR API calls to automatically track success/failure
    and basic metrics like page count and line count.

    This is NOT a pure technical library - it handles business logic
    like recording usage to state for billing purposes.
    """

    @staticmethod
    def recognize_and_track(
        image_path: str,
        state: Optional[Dict] = None,
        filename: str = ''
    ) -> str:
        """
        Perform OCR with automatic tracking

        This method wraps OCR API calls to automatically track success/failure
        and basic metrics like page count and line count.

        Args:
            image_path: Path to image file to recognize
            state: EmailState dict (optional, for tracking)
            filename: Original filename (for tracking and logging)

        Returns:
            Recognized text as a single string with newline separators

        Raises:
            Exception: If OCR API call fails

        Note:
            Azure OCR API doesn't return detailed usage metrics like tokens.
            We track success/failure, page count, and line count only.
            Unlike LLM calls, there's no fallback estimation mechanism.
        """
        config = AzureOCRConfig(**settings.AZURE_OCR_CONFIG)
        ocr_service = OCRService(config)

        try:
            logger.info(f"Recognizing image: {image_path}")
            result = ocr_service.recognize(
                image_path,
                skip_invalid=True,
                raw_response=True
            )

            if not hasattr(result, 'pages'):
                raise ValueError(
                    f"Expected Azure Document Intelligence response "
                    f"with 'pages' attribute, but got {type(result)}. "
                    f"Ensure raw_response=True is working correctly."
                )

            lines = []
            for page in result.pages:
                for line in page.lines:
                    lines.append(line.content)

            pages = len(result.pages)
            text = "\n".join(lines)

            if state is not None and settings.ENABLE_COST_TRACKING:
                state.setdefault('ocr_calls', []).append({
                    'filename': filename,
                    'success': True,
                    'pages': pages,
                    'lines_count': len(lines),
                    'timestamp': timezone.now().isoformat()
                })

            logger.info(
                f"OCR succeeded for {filename}: "
                f"{pages} page(s), {len(lines)} line(s)"
            )
            return text

        except Exception as e:
            logger.error(f"OCR failed for {filename}: {e}")

            if state is not None and settings.ENABLE_COST_TRACKING:
                state.setdefault('ocr_calls', []).append({
                    'filename': filename,
                    'success': False,
                    'pages': 0,
                    'error': str(e),
                    'timestamp': timezone.now().isoformat()
                })

            raise
