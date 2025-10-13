"""
Summary processing for audio file workflow.

This module provides summary processing that generates summaries from
audio file segments using LLM text generation. All data comes from
AudioFileState, no database queries are needed.
"""

from speechtotext.agents.nodes.base_node import BaseLangGraphNode
from speechtotext.agents.speechtotext_state import (
    AudioFileState,
    add_node_error
)
from speechtotext.utils import (
    call_llm,
    get_scene_prompt
)


class SummaryProcessingNode(BaseLangGraphNode):
    """
    Summary processing node for LangGraph workflow.

    This node handles the generation of summaries from audio file segments
    using LLM text generation.
    """

    def __init__(self):
        super().__init__("summary_processing_node")

    def before_processing(self, state: AudioFileState) -> AudioFileState:
        """
        Validate prerequisites before summary processing.

        Args:
            state (AudioFileState): Current audio file state

        Returns:
            AudioFileState: Updated state
        """
        audio_file_id = state['id']

        # Check required fields
        required_fields = ['id', 'segments', 'llm_language']
        missing_fields = [
            field for field in required_fields
            if not state.get(field)
        ]
        if missing_fields:
            error_msg = (
                f"Summary processing requires fields: {missing_fields}"
            )
            raise ValueError(error_msg)

        segments = state.get('segments', [])
        self.logger.info(
            f"Starting summary processing for AudioFile {audio_file_id}, "
            f"segments: {len(segments)}"
        )
        return state

    def execute_processing(self, state: AudioFileState) -> AudioFileState:
        """
        Execute the main summary processing logic.

        Args:
            state (AudioFileState): Current audio file state

        Returns:
            AudioFileState: Updated state with summary
        """
        audio_file_id = state['id']

        # Check if already completed
        if self._is_already_completed(state):
            self.logger.info(
                f"Summary processing already completed for AudioFile {audio_file_id}"
            )
            return state

        segments = state.get('segments', [])
        self.logger.info(
            f"Generating summary for AudioFile {audio_file_id}, "
            f"segments: {len(segments)}"
        )

        # Generate summary and update state
        summary_text = self._generate_summary(segments, state)
        state['summary'] = summary_text

        self.logger.info(
            f"Summary processing completed for AudioFile {audio_file_id}, "
            f"summary length: {len(summary_text) if summary_text else 0}"
        )
        return state

    def after_processing(self, state: AudioFileState) -> AudioFileState:
        """
        Validate processing results after summary processing.

        Args:
            state (AudioFileState): Current audio file state

        Returns:
            AudioFileState: Updated state
        """
        audio_file_id = state['id']
        summary = state.get('summary', '')

        if not summary:
            error_msg = "No summary generated from segments"
            self.logger.warning(error_msg)
            add_node_error(state, self.node_name, error_msg)
        else:
            self.logger.info(
                f"Summary processing validation completed for AudioFile {audio_file_id}, "
                f"summary length: {len(summary)}"
            )
        return state

    def _is_already_completed(self, state: AudioFileState) -> bool:
        """
        Check if summary processing is already completed.

        Args:
            state (AudioFileState): Current audio file state

        Returns:
            bool: True if already completed, False if needs processing
        """
        summary = state.get('summary', '')
        return bool(summary and summary.strip())

    def _generate_summary(self, segments: list, state: AudioFileState) -> str:
        """
        Generate summary from segments using LLM.

        Args:
            segments: List of segment data from AudioFileState
            state: Current audio file state

        Returns:
            str: Generated summary text
        """
        try:
            # Collect text content from segments
            content_parts = []
            for segment in segments:
                text_to_use = (
                    segment.get('llm_text') or segment.get('text', '')
                )
                if text_to_use:
                    content_parts.append(text_to_use)

            if not content_parts:
                self.logger.warning("No text content found in segments")
                return ""

            full_content = '\n\n'.join(content_parts)

            # Get scene and language settings from state or use defaults
            scene = state.get('scene', 'meeting')
            llm_language = state.get('llm_language')

            prompt = get_scene_prompt(scene, llm_language)
            summary_text = call_llm(prompt, full_content)

            self.logger.info(
                f"Generated summary with {len(summary_text)} characters"
            )
            return summary_text

        except Exception as e:
            self.logger.error(f"Error generating summary: {e}")
            return ""
