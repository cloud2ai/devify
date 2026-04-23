"""
Image intent processing node for email attachments.

This node sends image attachments directly to a multimodal LLM together
with the surrounding conversation context. It replaces the OCR-first path
for image understanding.
"""

from __future__ import annotations

import base64
import logging
import mimetypes
from pathlib import Path

from core.tracking import LLMTracker
from threadline.agents.email_state import EmailState, add_node_error
from threadline.agents.nodes.base_node import BaseLangGraphNode

logger = logging.getLogger(__name__)

IMAGE_INPUT_CHAR_LIMIT = 8000


class ImageIntentNode(BaseLangGraphNode):
    """
    Multimodal image understanding node.

    The node:
    - selects image attachments
    - builds conversation context from the current email state
    - calls a vision-capable LLM with the image bytes
    - stores the model output in attachment llm_content
    """

    def __init__(self):
        super().__init__("image_intent_node")

    def _build_conversation_context(self, state: EmailState) -> str | None:
        subject = (state.get("subject") or "").strip()
        sender = (state.get("sender") or "").strip()
        recipients = (state.get("recipients") or "").strip()
        received_at = (state.get("received_at") or "").strip()
        conversation_body = (
            state.get("text_content")
            or state.get("llm_content")
            or state.get("html_content")
            or ""
        ).strip()

        sections: list[str] = []
        if subject:
            sections.append(f"Subject: {subject}")
        if sender:
            sections.append(f"Sender: {sender}")
        if recipients:
            sections.append(f"Recipients: {recipients}")
        if received_at:
            sections.append(f"Received at: {received_at}")
        if conversation_body:
            sections.append(f"Conversation body:\n{conversation_body}")

        if not sections:
            return None
        return "\n\n".join(sections).strip()

    def _attachment_to_data_url(self, file_path: str) -> str:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Image file not found: {file_path}")

        mime_type, _ = mimetypes.guess_type(path.name)
        mime_type = mime_type or "image/png"
        payload = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{mime_type};base64,{payload}"

    def _build_messages(
        self,
        state: EmailState,
        attachment: dict,
        prompt: str,
    ) -> list[dict]:
        messages: list[dict] = [{"role": "system", "content": prompt}]

        user_blocks: list[dict] = []
        context = self._build_conversation_context(state)
        if context:
            if len(context) > IMAGE_INPUT_CHAR_LIMIT:
                context = (
                    context[:IMAGE_INPUT_CHAR_LIMIT].rstrip()
                    + "\n\n[Input truncated]"
                )
            user_blocks.append(
                {
                    "type": "text",
                    "text": "Conversation context:\n" + context,
                }
            )

        filename = attachment.get("filename") or ""
        safe_filename = attachment.get("safe_filename") or filename
        if filename or safe_filename:
            image_reference_lines = []
            if filename:
                image_reference_lines.append(f"Original filename: {filename}")
            if safe_filename and safe_filename != filename:
                image_reference_lines.append(
                    f"Stored filename: {safe_filename}"
                )
            user_blocks.append(
                {
                    "type": "text",
                    "text": "Image reference:\n"
                    + "\n".join(image_reference_lines),
                }
            )

        file_path = attachment.get("file_path")
        if not file_path:
            raise ValueError(
                f"Attachment {attachment.get('filename')} is missing file_path"
            )

        user_blocks.append(
            {
                "type": "image_url",
                "image_url": {"url": self._attachment_to_data_url(file_path)},
            }
        )

        messages.append({"role": "user", "content": user_blocks})
        return messages

    def can_enter_node(self, state: EmailState) -> bool:
        if not super().can_enter_node(state):
            return False

        attachments = state.get("attachments", [])
        has_images = any(att.get("is_image") for att in attachments)
        if not has_images:
            email_id = state.get("id")
            user_id = state.get("user_id")
            logger.info(
                f"No image attachments for email {email_id}, user {user_id}, "
                f"skipping image intent processing"
            )
            return False

        return True

    def execute_processing(self, state: EmailState) -> EmailState:
        attachments = state.get("attachments", [])
        force = state.get("force", False)
        max_attachments = state.get("max_attachments")
        updated_attachments = []

        image_count = 0
        processed_count = 0
        skipped_count = 0
        limit_skipped_count = 0
        failed_attachments = []

        image_attachments = [att for att in attachments if att.get("is_image")]
        non_image_attachments = [
            att for att in attachments if not att.get("is_image")
        ]
        image_attachments.sort(
            key=lambda x: x.get("file_size", 0),
            reverse=True,
        )

        if (
            max_attachments is not None
            and len(image_attachments) > max_attachments
        ):
            attachments_to_process = image_attachments[:max_attachments]
            attachments_over_limit = image_attachments[max_attachments:]
            logger.info(
                f"Attachment limit: {max_attachments}, will process "
                f"{len(attachments_to_process)} images, skip "
                f"{len(attachments_over_limit)} images due to limit"
            )
        else:
            attachments_to_process = image_attachments
            attachments_over_limit = []

        for attachment in non_image_attachments:
            logger.info(
                f"Non-image attachment {attachment.get('filename')} "
                f"skipped image intent processing"
            )
            updated_attachments.append(attachment)

        prompt_config = state.get("prompt_config")
        if not prompt_config:
            error_message = "No prompt_config found in State"
            logger.error(error_message)
            return add_node_error(state, self.node_name, error_message)

        image_llm_config_uuid = state.get("image_llm_config_uuid")
        if not image_llm_config_uuid:
            error_message = "Missing image_llm_config_uuid in State"
            logger.error(error_message)
            return add_node_error(state, self.node_name, error_message)

        image_prompt = prompt_config.get(
            "image_intent_prompt"
        ) or prompt_config.get("ocr_prompt")
        if not image_prompt:
            error_message = "Missing image_intent_prompt in prompt_config"
            logger.error(error_message)
            return add_node_error(state, self.node_name, error_message)

        for attachment in attachments_to_process:
            image_count += 1

            if not force and attachment.get("llm_content"):
                logger.info(
                    f"Attachment {attachment.get('filename')} already has "
                    f"LLM content, skipping in normal mode"
                )
                updated_attachments.append(attachment)
                skipped_count += 1
                continue

            try:
                logger.info(
                    f"Processing attachment {attachment.get('filename')} "
                    f"with multimodal LLM"
                )

                messages = self._build_messages(
                    state=state,
                    attachment=attachment,
                    prompt=image_prompt,
                )

                llm_result, _usage = LLMTracker.call_messages_and_track(
                    messages=messages,
                    json_mode=False,
                    state=state,
                    node_name=self.node_name,
                    model_uuid=image_llm_config_uuid,
                )
                llm_content = llm_result.strip() if llm_result else ""

                if llm_content:
                    attachment["llm_content"] = llm_content
                    logger.info(
                        f"Multimodal image processing successful for "
                        f"{attachment.get('filename')}"
                    )
                else:
                    attachment["llm_content"] = ""
                    logger.warning(
                        f"Multimodal image processing completed for "
                        f"{attachment.get('filename')} - no content generated"
                    )

                processed_count += 1

            except Exception as e:
                logger.error(
                    f"Multimodal image processing failed for "
                    f"{attachment.get('filename')}: {e}"
                )
                attachment["llm_content"] = ""
                failed_attachments.append(
                    {
                        "id": attachment.get("id"),
                        "filename": attachment.get("filename"),
                        "error": str(e),
                    }
                )

            updated_attachments.append(attachment)

        for attachment in attachments_over_limit:
            attachment["skip_reason"] = "PLAN_LIMIT_EXCEEDED"
            attachment["llm_content"] = ""
            updated_attachments.append(attachment)
            limit_skipped_count += 1

        email_id = state.get("id")
        user_id = state.get("user_id")

        if limit_skipped_count > 0:
            logger.warning(
                f"[{self.node_name}] {limit_skipped_count} attachments "
                f"skipped due to plan limit (max: {max_attachments})"
            )

        logger.info(
            f"[{self.node_name}] Multimodal processing completed for email "
            f"{email_id}, user {user_id}: {image_count} images, "
            f"{processed_count} processed, {skipped_count} skipped, "
            f"{limit_skipped_count} over limit"
        )

        updated_state = {
            **state,
            "attachments": updated_attachments,
        }

        if failed_attachments:
            failed_files = ", ".join(
                [
                    f"{item['filename']}({item['error']})"
                    for item in failed_attachments
                ]
            )
            logger.warning(
                f"Multimodal processing failed for "
                f"{len(failed_attachments)} attachments: {failed_files}. "
                "These attachments will be skipped but workflow will continue."
            )

        return updated_state
