import logging

from django.conf import settings

from devtoolbox.ocr import OCRService
from devtoolbox.ocr.azure_provider import AzureOCRConfig

logger = logging.getLogger(__name__)


class OCRHandler:
    def __init__(self):
        config = AzureOCRConfig(**settings.AZURE_OCR_CONFIG)
        self.client = OCRService(config)

    def recognize(self, image_path: str) -> str:
        logger.info(f"Recognizing image: {image_path}")
        lines = self.client.recognize(image_path, skip_invalid=True)
        return "\n".join(lines)
