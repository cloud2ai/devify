"""
LLM Attachment processing node for email attachments.

This node processes OCR content using LLM to extract structured information.
It operates purely on State without database access.
"""

import logging

from core.tracking import LLMTracker
from threadline.agents.email_state import EmailState, add_node_error
from threadline.agents.nodes.base_node import BaseLangGraphNode

logger = logging.getLogger(__name__)

OCR_INPUT_CHAR_LIMIT = 8000


class LLMAttachmentNode(BaseLangGraphNode):
    """
    LLM Attachment processing node.

    This node processes OCR content from image attachments using LLM
    to extract and organize structured information.

    State Input Requirements:
    - attachments: List of attachment data with OCR content
    - prompt_config: User's prompt configuration (from workflow_prepare)

    Responsibilities:
    - Check for image attachments with OCR content in State
    - Read prompt configuration from State (no database access)
    - Execute LLM processing on OCR content
    - Update attachments with llm_content in State
    - Skip attachments that already have LLM content (unless force mode)
    - Handle LLM errors gracefully
    """

    def __init__(self):
        super().__init__("llm_attachment_node")

    def _build_ocr_context(self, state: EmailState) -> str | None:
        """
        Build OCR context for LLM input.

        Prefer raw conversation text so OCR reasoning uses the original
        dialogue as context. Only fall back to existing LLM-organized content
        when no raw text is available.
        """
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

        sections = []
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

    def _build_ocr_llm_input(
        self,
        state: EmailState,
        attachment: dict,
        cleaned_ocr_content: str,
    ) -> str:
        prompt_parts = []
        ocr_context = self._build_ocr_context(state)
        if ocr_context:
            prompt_parts.append("Conversation context:\n" f"{ocr_context}")

        filename = attachment.get("filename") or ""
        safe_filename = attachment.get("safe_filename") or filename
        image_refs = []
        if filename:
            image_refs.append(f"Original filename: {filename}")
        if safe_filename and safe_filename != filename:
            image_refs.append(f"Stored filename: {safe_filename}")
        if image_refs:
            prompt_parts.append("Image reference:\n" + "\n".join(image_refs))

        prompt_parts.append("Cleaned OCR content:\n" f"{cleaned_ocr_content}")
        llm_input = "\n\n".join(prompt_parts).strip()
        if len(llm_input) > OCR_INPUT_CHAR_LIMIT:
            llm_input = (
                llm_input[:OCR_INPUT_CHAR_LIMIT].rstrip()
                + "\n\n[Input truncated]"
            )
        return llm_input

    def can_enter_node(self, state: EmailState) -> bool:
        """
        Check if LLM Attachment node can enter.

        LLM Attachment node can enter if:
        - No errors in previous nodes (or force mode)
        - Has image attachments with OCR content to process

        Args:
            state (EmailState): Current email state

        Returns:
            bool: True if node can enter, False otherwise
        """
        if not super().can_enter_node(state):
            return False

        attachments = state.get("attachments", [])
        has_ocr_content = any(
            att.get("is_image") and att.get("ocr_content", "").strip()
            for att in attachments
        )

        if not has_ocr_content:
            logger.info(
                "No image attachments with OCR content, "
                "skipping LLM processing"
            )
            return False

        return True

    def execute_processing(self, state: EmailState) -> EmailState:
        """
        Execute LLM processing on attachment OCR content.

        Reads attachments from State, performs LLM processing on OCR content,
        and updates State with LLM results.

        Only processes attachments within the user's plan limit.
        Attachments marked with skip_reason will be skipped.

        Args:
            state (EmailState): Current email state

        Returns:
            EmailState: Updated state with LLM results
        """
        attachments = state.get("attachments", [])
        force = state.get("force", False)
        updated_attachments = []

        image_count = 0
        processed_count = 0
        skipped_count = 0
        limit_skipped_count = 0
        failed_attachments = []

        prompt_config = state.get("prompt_config")
        if not prompt_config:
            error_message = "No prompt_config found in State"
            logger.error(error_message)
            return add_node_error(state, self.node_name, error_message)
        image_llm_config_uuid = state.get("image_llm_config_uuid")

        ocr_cleanup_prompt = prompt_config.get("ocr_cleanup_prompt")
        ocr_prompt = prompt_config.get("ocr_prompt")
        if not ocr_prompt:
            error_message = "Missing ocr_prompt in prompt_config"
            logger.error(error_message)
            return add_node_error(state, self.node_name, error_message)

        for attachment in attachments:
            if not attachment.get("is_image"):
                logger.info(
                    f"Non-image attachment {attachment.get('filename')} "
                    f"skipped LLM processing"
                )
                updated_attachments.append(attachment)
                continue

            # Skip attachments that exceeded plan limit
            if attachment.get("skip_reason") == "PLAN_LIMIT_EXCEEDED":
                logger.info(
                    f"Attachment {attachment.get('filename')} skipped due to "
                    f"plan limit, will not process with LLM"
                )
                attachment["llm_content"] = ""
                updated_attachments.append(attachment)
                limit_skipped_count += 1
                continue

            ocr_content = attachment.get("ocr_content", "").strip()
            if not ocr_content:
                logger.warning(
                    f"Attachment {attachment.get('filename')} has no OCR "
                    f"content, skipping LLM processing"
                )
                attachment["llm_content"] = ""
                updated_attachments.append(attachment)
                continue

            image_count += 1

            if not force and attachment.get("llm_content"):
                logger.info(
                    f"Attachment {attachment.get('filename')} already "
                    f"has LLM content, skipping in normal mode"
                )
                updated_attachments.append(attachment)
                skipped_count += 1
                continue

            try:
                logger.info(
                    f"Processing attachment {attachment.get('filename')} "
                    f"with LLM"
                )

                cleaned_stage_content = (
                    attachment.get("ocr_cleaned_content", "") or ""
                ).strip()
                cleaned_ocr_content = cleaned_stage_content or ocr_content

                if not force and cleaned_stage_content:
                    logger.info(
                        f"Reusing cached OCR cleaned content for "
                        f"{attachment.get('filename')}"
                    )
                elif ocr_cleanup_prompt:
                    try:
                        cleaned_result, _cleanup_usage = (
                            LLMTracker.call_and_track(
                                prompt=ocr_cleanup_prompt,
                                content=ocr_content,
                                json_mode=False,
                                state=state,
                                node_name=self.node_name,
                                model_uuid=image_llm_config_uuid,
                            )
                        )
                        cleaned_result = (
                            cleaned_result.strip() if cleaned_result else ""
                        )
                        if cleaned_result:
                            cleaned_ocr_content = cleaned_result
                            attachment["ocr_cleaned_content"] = (
                                cleaned_ocr_content
                            )
                        logger.info(
                            f"OCR cleanup completed for "
                            f"{attachment.get('filename')}"
                        )
                    except Exception as cleanup_error:
                        logger.warning(
                            f"OCR cleanup failed for "
                            f"{attachment.get('filename')}: "
                            f"{cleanup_error}. Falling back to raw OCR."
                        )
                attachment["ocr_cleaned_content"] = cleaned_ocr_content

                llm_input = self._build_ocr_llm_input(
                    state=state,
                    attachment=attachment,
                    cleaned_ocr_content=cleaned_ocr_content,
                )

                llm_result, usage = LLMTracker.call_and_track(
                    prompt=ocr_prompt,
                    content=llm_input,
                    json_mode=False,
                    state=state,
                    node_name=self.node_name,
                    model_uuid=image_llm_config_uuid,
                )
                llm_content = llm_result.strip() if llm_result else ""

                if llm_content:
                    attachment["llm_content"] = llm_content
                    logger.info(
                        f"LLM processing successful for "
                        f"{attachment.get('filename')}"
                    )
                else:
                    attachment["llm_content"] = ""
                    logger.warning(
                        f"LLM processing completed for "
                        f"{attachment.get('filename')} - "
                        f"no content generated"
                    )

                processed_count += 1

            except Exception as e:
                logger.error(
                    f"LLM processing failed for "
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

        if limit_skipped_count > 0:
            logger.warning(
                f"{limit_skipped_count} attachments skipped due to plan limit"
            )

        logger.info(
            f"LLM Attachment processing completed: {image_count} images, "
            f"{processed_count} processed, {skipped_count} skipped, "
            f"{limit_skipped_count} over limit"
        )

        updated_state = {**state, "attachments": updated_attachments}

        if failed_attachments:
            failed_files = ", ".join(
                [
                    f"{item['filename']}({item['error']})"
                    for item in failed_attachments
                ]
            )
            logger.warning(
                f"LLM Attachment processing failed for "
                f"{len(failed_attachments)} "
                f"attachments: {failed_files}. These attachments will be "
                f"skipped but workflow will continue."
            )

        return updated_state
