"""
OCR processing node for email attachments.

This node processes image attachments using OCR to extract text content.
It operates purely on State without database access.
"""

import logging
from typing import Any, Dict, List

from core.tracking import OCRTracker
from threadline.agents.email_state import EmailState, add_node_error
from threadline.agents.nodes.base_node import BaseLangGraphNode

logger = logging.getLogger(__name__)


class OCRNode(BaseLangGraphNode):
    """
    OCR processing node for image attachments.

    This node extracts text from image attachments using OCR.
    It updates the attachments in State with ocr_content field.

    Responsibilities:
    - Check for image attachments in State
    - Execute OCR on each image attachment
    - Update attachments with ocr_content in State
    - Skip attachments that already have OCR content (unless force mode)
    - Handle OCR errors gracefully
    """

    def __init__(self):
        super().__init__("ocr_node")

    def can_enter_node(self, state: EmailState) -> bool:
        """
        Check if OCR node can enter.

        OCR node can enter if:
        - No errors in previous nodes (or force mode)
        - Has attachments to process

        Args:
            state (EmailState): Current email state

        Returns:
            bool: True if node can enter, False otherwise
        """
        if not super().can_enter_node(state):
            return False

        attachments = state.get('attachments', [])
        has_images = any(att.get('is_image') for att in attachments)

        if not has_images:
            email_id = state.get('id')
            user_id = state.get('user_id')
            logger.info(
                f"No image attachments for email {email_id}, "
                f"user {user_id}, skipping OCR"
            )
            return False

        return True

    def execute_processing(self, state: EmailState) -> EmailState:
        """
        Execute OCR processing on image attachments.

        Reads attachments from State, performs OCR on images,
        and updates State with OCR results.

        Args:
            state (EmailState): Current email state

        Returns:
            EmailState: Updated state with OCR results
        """
        attachments = state.get('attachments', [])
        force = state.get('force', False)
        updated_attachments = []

        image_count = 0
        processed_count = 0
        skipped_count = 0
        failed_attachments = []

        for attachment in attachments:
            if not attachment.get('is_image'):
                logger.info(
                    f"Non-image attachment {attachment.get('filename')} "
                    f"skipped OCR processing"
                )
                updated_attachments.append(attachment)
                continue

            image_count += 1

            if not force and attachment.get('ocr_content'):
                logger.info(
                    f"Attachment {attachment.get('filename')} already "
                    f"has OCR content, skipping in normal mode"
                )
                updated_attachments.append(attachment)
                skipped_count += 1
                continue

            try:
                file_path = attachment.get('file_path')
                logger.info(
                    f"Processing attachment {attachment.get('filename')} "
                    f"({file_path})"
                )

                text = OCRTracker.recognize_and_track(
                    image_path=file_path,
                    state=state,
                    filename=attachment.get('filename', '')
                )

                if text and text.strip():
                    attachment['ocr_content'] = text.strip()
                    logger.info(
                        f"OCR successful for {attachment.get('filename')}"
                    )
                else:
                    attachment['ocr_content'] = ''
                    logger.warning(
                        f"OCR completed for "
                        f"{attachment.get('filename')} - "
                        f"no content recognized"
                    )

                processed_count += 1

            except Exception as e:
                logger.error(
                    f"OCR failed for {attachment.get('filename')}: {e}"
                )
                attachment['ocr_content'] = ''
                failed_attachments.append({
                    'id': attachment.get('id'),
                    'filename': attachment.get('filename'),
                    'error': str(e)
                })

            updated_attachments.append(attachment)

        email_id = state.get('id')
        user_id = state.get('user_id')
        logger.info(
            f"[{self.node_name}] OCR completed for email {email_id}, "
            f"user {user_id}: {image_count} images, "
            f"{processed_count} processed, {skipped_count} skipped"
        )

        updated_state = {
            **state,
            'attachments': updated_attachments
        }

        if failed_attachments:
            failed_files = ', '.join([
                f"attachment_{item['id']}({item['error']})"
                for item in failed_attachments
            ])
            error_message = (
                f'OCR failed for {len(failed_attachments)} image '
                f'attachments: {failed_files}'
            )
            updated_state = add_node_error(
                updated_state,
                self.node_name,
                error_message
            )
            logger.error(error_message)

        return updated_state
