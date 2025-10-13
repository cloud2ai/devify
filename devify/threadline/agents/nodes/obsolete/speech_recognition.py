"""
Speech recognition node for audio file processing workflow.

This node handles the speech recognition phase of the audio processing
pipeline, converting audio files to text segments with timing information.
"""

import logging
import tempfile

from speechtotext.agents.nodes.base_node import BaseLangGraphNode
from speechtotext.agents.speechtotext_state import (
    AudioFileState,
    add_node_error
)
from speechtotext.utils import download_audio_file, recognize_speech

logger = logging.getLogger(__name__)


class SpeechRecognitionNode(BaseLangGraphNode):
    """
    Node responsible for speech recognition processing.

    This node converts audio files to text segments with timing information.
    It handles downloading audio files, performing speech recognition, and
    storing the results as audio file segments.
    """

    def __init__(self):
        super().__init__("speech_recognition_node")


    def before_processing(self, state: AudioFileState) -> AudioFileState:
        """
        Validate audio file and prepare for speech recognition.

        Args:
            state (AudioFileState): Current audio file state

        Returns:
            AudioFileState: Updated state

        Raises:
            ValueError: If audio file not found or invalid
        """
        # Check required fields
        required_fields = [
            'id',
            'storage_path',
            'storage_bucket',
            'asr_languages'
        ]
        missing_fields = [
            field for field in required_fields
            if not state.get(field)
        ]

        if missing_fields:
            error_msg = (
                f"Speech recognition requires fields: {missing_fields}"
            )
            raise ValueError(error_msg)

        audio_file_id = state['id']

        self.logger.info(
            f"Starting speech recognition for AudioFile {audio_file_id}"
        )
        return state

    def execute_processing(self, state: AudioFileState) -> AudioFileState:
        """
        Execute speech recognition processing.

        Downloads the audio file, performs speech recognition, and stores
        the results in the state for later database synchronization.

        Args:
            state (AudioFileState): Current audio file state

        Returns:
            AudioFileState: Updated state with recognition results
        """
        try:
            # Get data from state
            audio_file_id = state['id']
            storage_path = state['storage_path']
            asr_languages = state['asr_languages']

            # Download and process audio file
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_audio_path, file_size = download_audio_file(
                    storage_path, temp_dir
                )
                self.logger.info(
                    f"Downloaded audio file: {audio_file_id}"
                )

                # Perform speech recognition
                recognition_result = recognize_speech(
                    temp_audio_path,
                    temp_dir,
                    languages=asr_languages
                )

                # Process recognition result and store in state
                self._process_recognition_result(state, recognition_result)

                self.logger.info(
                    f"Speech recognition completed: {audio_file_id}"
                )

        except Exception as e:
            error_msg = f"Speech recognition failed: {str(e)}"
            self.logger.error(error_msg)
            add_node_error(state, self.node_name, error_msg)
            raise

        return state

    def after_processing(self, state: AudioFileState) -> AudioFileState:
        """
        Validate recognition results and perform cleanup.

        Args:
            state (AudioFileState): Current audio file state

        Returns:
            AudioFileState: Updated state
        """
        # Validate recognition results
        segments = state.get('segments', [])
        if not segments:
            error_msg = "No speech segments generated from recognition"
            self.logger.warning(error_msg)
            add_node_error(state, self.node_name, error_msg)
        else:
            # Validate segments have text content
            segments_with_text = [
                seg for seg in segments
                if seg.get('text', '').strip()
            ]
            if not segments_with_text:
                error_msg = "No segments with transcription text generated"
                self.logger.warning(error_msg)
                add_node_error(state, self.node_name, error_msg)

        audio_file_id = state['id']
        self.logger.info(
            f"Speech recognition validation completed for "
            f"AudioFile {audio_file_id}"
        )
        return state


    def _process_recognition_result(
        self,
        state: AudioFileState,
        recognition_result: dict
    ) -> None:
        """
        Process the speech recognition result and store in state.

        Args:
            state (AudioFileState): Current audio file state
            recognition_result (dict): Recognition result from devtoolbox
        """
        try:
            audio_file_id = state['id']
            self.logger.info(
                f"Processing recognition result: {audio_file_id}"
            )

            metadata = recognition_result.get('metadata', {})
            transcription_text = recognition_result.get('transcription', '')

            if not transcription_text:
                self.logger.warning("No transcription text received")

            # Update audio metadata in state
            self._update_audio_metadata_in_state(state, metadata)

            # Process segments
            chunks = metadata.get('chunks', [])
            self.logger.info(f"Processing {len(chunks)} audio chunks")

            segments = []
            for chunk in chunks:
                segment = self._create_segment_from_chunk(chunk)
                segments.append(segment)

            # Store segments in state for later database sync
            state['segments'] = segments
            state['segments_total_count'] = len(segments)

            self.logger.info(
                f"Recognition result processed: {audio_file_id}, "
                f"segments: {len(segments)}"
            )

        except Exception as e:
            error_msg = f"Error processing recognition result: {str(e)}"
            self.logger.error(error_msg)
            raise

    def _update_audio_metadata_in_state(
        self,
        state: AudioFileState,
        metadata: dict
    ) -> None:
        """
        Update audio metadata in state from recognition result.

        Args:
            state (AudioFileState): Current audio file state
            metadata (dict): Metadata from recognition result
        """
        audio_info = metadata.get('audio_info', {})
        storage_info = metadata.get('storage_info', {})

        # Update duration
        duration_ms = audio_info.get('total_duration')
        if duration_ms is not None:
            state['duration'] = duration_ms / 1000.0

        # Update sample rate
        sample_rate = audio_info.get('sample_rate')
        if sample_rate is not None:
            state['sample_rate'] = sample_rate

        # Update channels
        channels = audio_info.get('channels')
        if channels is not None:
            state['channels'] = channels

        # Update bit rate
        self._update_bit_rate_in_state(state, storage_info)

        # Update format
        storage_format = storage_info.get('storage_format')
        if storage_format:
            state['format'] = storage_format
        else:
            original_format = audio_info.get('original_format')
            if original_format:
                state['format'] = original_format

        # Update file size
        file_size = storage_info.get('total_mp3_size')
        if file_size is not None:
            state['file_size'] = file_size
        else:
            wav_size = storage_info.get('total_wav_size')
            if wav_size is not None:
                state['file_size'] = wav_size

    def _update_bit_rate_in_state(
        self,
        state: AudioFileState,
        storage_info: dict
    ) -> None:
        """
        Update bit rate in state from storage information.

        Args:
            state (AudioFileState): Current audio file state
            storage_info (dict): Storage information from metadata
        """
        bitrate_str = storage_info.get('storage_bitrate')
        if not bitrate_str:
            return

        try:
            if isinstance(bitrate_str, str) and bitrate_str.endswith('k'):
                state['bit_rate'] = int(float(bitrate_str[:-1]) * 1000)
            else:
                state['bit_rate'] = int(bitrate_str)
        except (ValueError, TypeError) as e:
            self.logger.warning(
                f"Failed to parse bitrate '{bitrate_str}': {e}"
            )

    def _create_segment_from_chunk(self, chunk: dict) -> dict:
        """
        Create a segment dictionary from a recognition chunk.

        Args:
            chunk (dict): Recognition chunk data

        Returns:
            dict: Segment data for state storage
        """
        index = chunk.get('index', 0)
        start_time = chunk.get('start_time_in_ms', 0.0) / 1000.0
        end_time = chunk.get('end_time_in_ms', 0.0) / 1000.0
        duration = chunk.get('duration_in_ms', 0.0) / 1000.0
        text = chunk.get('transcript', '')

        return {
            'segment_order': index,
            'start_time': start_time,
            'end_time': end_time,
            'duration': duration,
            'speaker': '',
            'text': text,
            'asr_error': '',  # Will be populated by ASR processing
            'llm_error': ''   # Will be populated by LLM processing
        }
