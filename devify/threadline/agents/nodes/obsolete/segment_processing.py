"""
Segment processing for audio file workflow.

This module provides segment processing that optimizes audio file segments
using LLM text optimization. All data comes from AudioFileState, no database
queries are needed.
"""

from typing import List

from speechtotext.agents.nodes.base_node import BaseLangGraphNode
from speechtotext.agents.speechtotext_state import (
    AudioFileState,
    add_node_error
)
from speechtotext.utils import (
    call_llm,
    get_optimization_prompt
)


class SegmentProcessingNode(BaseLangGraphNode):
    """
    Segment processing node for LangGraph workflow.

    This node handles the optimization of audio file segments using LLM
    text optimization.
    """

    def __init__(self):
        super().__init__("segment_processing_node")

    def before_processing(self, state: AudioFileState) -> AudioFileState:
        """
        Validate prerequisites before segment processing.

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
                f"Segment processing requires fields: {missing_fields}"
            )
            raise ValueError(error_msg)

        segments = state.get('segments', [])
        if not segments:
            error_msg = "No segments found for LLM processing"
            raise ValueError(error_msg)

        self.logger.info(
            f"Starting segment processing for AudioFile {audio_file_id}, "
            f"segments: {len(segments)}"
        )
        return state

    def execute_processing(self, state: AudioFileState) -> AudioFileState:
        """
        Execute the main segment processing logic.

        Args:
            state (AudioFileState): Current audio file state

        Returns:
            AudioFileState: Updated state with processed segments
        """
        audio_file_id = state['id']
        segments = state.get('segments', [])

        # Check if already completed
        if self._is_already_completed(segments):
            self.logger.info(
                f"Segment processing already completed for "
                f"AudioFile {audio_file_id}"
            )
            return state

        # Filter segments that need processing
        segments_to_process = [
            segment for segment in segments
            if not segment.get('llm_text')
        ]

        if not segments_to_process:
            self.logger.info(
                f"All segments already processed for AudioFile {audio_file_id}"
            )
            return state

        self.logger.info(
            f"Processing {len(segments_to_process)} segments for "
            f"AudioFile {audio_file_id}"
        )

        # Process segments and update state
        processed_segments = self._process_segments(segments_to_process, state)

        # Update state with processed segments
        self._update_segments_in_state(state, segments, processed_segments)

        self.logger.info(
            f"Segment processing completed for AudioFile {audio_file_id}, "
            f"processed: {len(processed_segments)}"
        )
        return state

    def after_processing(self, state: AudioFileState) -> AudioFileState:
        """
        Validate processing results after segment processing.

        Args:
            state (AudioFileState): Current audio file state

        Returns:
            AudioFileState: Updated state
        """
        audio_file_id = state['id']
        segments = state.get('segments', [])

        if not segments:
            error_msg = "No segments found after processing"
            self.logger.warning(error_msg)
            add_node_error(state, self.node_name, error_msg)
            return state

        # Check if all segments have been processed
        processed_count = self._get_processed_segments_count(segments)
        if processed_count == 0:
            error_msg = "No segments were successfully processed by LLM"
            self.logger.warning(error_msg)
            add_node_error(state, self.node_name, error_msg)

        # Log segment processing validation result with processed count
        self.logger.info(
            f"Segment processing validation completed for AudioFile "
            f"{audio_file_id}, processed: {processed_count}/{len(segments)}"
        )
        return state

    def _is_already_completed(self, segments: List[dict]) -> bool:
        """
        Check if segment processing is already completed.

        Args:
            segments: List of segments to check

        Returns:
            bool: True if all segments are already processed
        """
        if not segments:
            return False
        return all(segment.get("llm_text") for segment in segments)

    def _get_processed_segments_count(self, segments: List[dict]) -> int:
        """
        Count segments that have been processed by LLM.

        Args:
            segments: List of segments to count

        Returns:
            int: Number of segments with llm_text
        """
        return sum(1 for segment in segments if segment.get('llm_text'))

    def _update_segments_in_state(
        self,
        state: AudioFileState,
        original_segments: List[dict],
        processed_segments: List[dict]
    ) -> None:
        """
        Update state with processed segments.

        Args:
            state: Current audio file state
            original_segments: Original segments from state
            processed_segments: Newly processed segments
        """
        # Create mapping of processed segments by segment_order
        processed_by_order = {
            p.get('segment_order'): p for p in processed_segments
        }

        # Merge processed segments with original ones
        updated_segments = []
        for segment in original_segments:
            segment_order = segment.get('segment_order')
            updated_segments.append(
                processed_by_order.get(segment_order, segment)
            )

        # Update state
        state['segments'] = updated_segments
        state['segments_total_count'] = len(updated_segments)

    def _process_segments(
        self, segments_to_process: List[dict], state: AudioFileState
    ) -> List[dict]:
        """
        Process segments using LLM optimization.

        Args:
            segments_to_process: List of segments that need processing
            state: Current audio file state

        Returns:
            List of processed segments with llm_text added
        """
        processed_segments = []
        successful_count = 0
        failed_count = 0

        # Get LLM language from state (cached in WorkflowPrepareNode)
        llm_language = state.get('llm_language', 'en-US')

        for segment in segments_to_process:
            try:
                # Create copy to avoid modifying original
                processed_segment = segment.copy()

                # Get text to process
                text_to_process = segment.get('text', '')
                if not text_to_process:
                    segment_order = segment.get('segment_order', 'unknown')
                    self.logger.warning(
                        f"No text found for segment {segment_order}"
                    )
                    processed_segment['llm_error'] = (
                        "No text content to process"
                    )
                    failed_count += 1
                else:
                    # Call LLM for optimization
                    prompt = get_optimization_prompt(llm_language)
                    optimized_text = call_llm(prompt, text_to_process)

                    # Update segment with LLM result
                    processed_segment['llm_text'] = optimized_text
                    processed_segment['llm_error'] = None
                    successful_count += 1

                    segment_order = segment.get('segment_order', 'unknown')
                    self.logger.info(
                        f"Text optimization completed for segment {segment_order}"
                    )

            except Exception as e:
                segment_order = segment.get('segment_order', 'unknown')
                self.logger.error(
                    f"Error optimizing text for segment {segment_order}: {e}"
                )
                processed_segment['llm_error'] = str(e)
                failed_count += 1

            processed_segments.append(processed_segment)

        # Log processing results
        if failed_count == 0:
            self.logger.info(
                f"All {successful_count} segments processed successfully"
            )
        else:
            self.logger.warning(
                f"Processed {successful_count} segments, "
                f"{failed_count} failed"
            )

        return processed_segments
