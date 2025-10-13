"""
Workflow prepare node for audio file processing.

This node handles all initial validation, database setup, and state
preparation when starting the speech processing workflow. It serves as
the single entry point for all database validations and initializations.
"""

import logging
from typing import Dict, Any

from speechtotext.agents.nodes.base_node import BaseLangGraphNode
from speechtotext.agents.speechtotext_state import (
    AudioFileState,
    add_node_error
)
from speechtotext.models import (
    AudioFile,
    ProcessingStatus
)

logger = logging.getLogger(__name__)


class WorkflowPrepareNode(BaseLangGraphNode):
    """
    Workflow prepare node for LangGraph workflow.

    This node serves as the single entry point for all database
    validations, initializations, and state preparation. It ensures all
    necessary data is loaded into the AudioFileState, eliminating the
    need for subsequent nodes to perform database queries.

    Responsibilities:
    - Validate audio_file_id and load AudioFile object
    - Validate processing prerequisites and status
    - Initialize AudioFileState with all necessary data
    - Set database status to PROCESSING
    - Provide comprehensive validation for the entire workflow
    """

    def __init__(self):
        super().__init__("workflow_prepare_node")
        self.audio_file = None

    def can_enter_node(self, state: AudioFileState) -> bool:
        """
        Check if workflow prepare node can enter.

        Workflow prepare is the entry point, so we use simpler logic:
        - Force mode: always allow entry
        - Normal mode: check for existing errors

        Args:
            state (AudioFileState): Current audio file state

        Returns:
            bool: True if node can enter, False otherwise
        """
        force = state.get('force', False)
        if force:
            # Force mode: always allow entry
            self.logger.info("Force mode: allowing workflow preparation")
            return True

        # Normal mode: use parent's error checking
        return super().can_enter_node(state)

    def before_processing(self, state: AudioFileState) -> AudioFileState:
        """
        Pre-processing: Basic validation and load AudioFile.

        Args:
            state (AudioFileState): Current audio file state

        Returns:
            AudioFileState: Updated state after basic validation
        """
        # Validate audio_file_id in state
        audio_file_id = state.get('id')
        if not audio_file_id:
            raise ValueError('audio_file_id is required in state')

        # Load AudioFile from database
        try:
            self.audio_file = AudioFile.objects.get(id=audio_file_id)
        except AudioFile.DoesNotExist:
            raise ValueError(f'AudioFile {audio_file_id} not found')

        self.logger.info(f"AudioFile {audio_file_id} loaded for processing")
        return state

    def execute_processing(self, state: AudioFileState) -> AudioFileState:
        """
        Execute the workflow preparation logic.

        Populate the AudioFileState with all data from the database AudioFile.
        Optionally set database status to PROCESSING based on force parameter.

        Args:
            state (AudioFileState): Current audio file state

        Returns:
            AudioFileState: Updated state with all audio file data
        """
        # Get force parameter from state
        force = state.get('force', False)

        # Set database status to PROCESSING (unless in force mode)
        if not force:
            self.audio_file.set_status(ProcessingStatus.PROCESSING.value)
            self.logger.info(
                f"AudioFile {self.audio_file.id} status set to PROCESSING"
            )
        else:
            self.logger.info(
                f"Force mode: skipping status update, "
                f"current status remains {self.audio_file.status}"
            )

        # Update state with all AudioFile data
        updated_state = {
            **state,
            'id': str(self.audio_file.id),
            'user_id': str(self.audio_file.user_id),
            'display_name': self.audio_file.display_name,
            'file_size': self.audio_file.file_size,
            'file_md5': self.audio_file.file_md5,
            'duration': self.audio_file.duration,
            'format': self.audio_file.format,
            'storage_path': self.audio_file.storage_path,
            'storage_bucket': self.audio_file.storage_bucket,
            'sample_rate': self.audio_file.sample_rate,
            'channels': self.audio_file.channels,
            'bit_rate': self.audio_file.bit_rate,
            'asr_languages': self.audio_file.asr_languages,
            'llm_language': self.audio_file.llm_language,
            'scene': self.audio_file.scene,
            'created_at': (
                self.audio_file.created_at.isoformat()
                if self.audio_file.created_at else None
            ),
            'updated_at': (
                self.audio_file.updated_at.isoformat()
                if self.audio_file.updated_at else None
            )
        }

        self.logger.info(
            f"AudioFileState populated for {self.audio_file.id} - "
            f"all data loaded from database"
        )

        return updated_state

    def after_processing(self, state: AudioFileState) -> AudioFileState:
        """
        Post-processing: Basic validation of critical fields for subsequent nodes.

        Check essential fields that will be needed by downstream processing nodes.
        This helps catch configuration issues early rather than failing later.

        Args:
            state (AudioFileState): Current audio file state

        Returns:
            AudioFileState: Validated state

        Raises:
            ValueError: If critical fields are missing
        """
        # Check storage-related fields (required for file access)
        if not state.get('storage_path'):
            raise ValueError(
                f"AudioFile {state.get('id')} missing storage_path - "
                f"required for file access in subsequent processing"
            )

        if not state.get('storage_bucket'):
            raise ValueError(
                f"AudioFile {state.get('id')} missing storage_bucket - "
                f"required for file access in subsequent processing"
            )

        # Check language configuration (required for ASR and LLM processing)
        if not state.get('asr_languages'):
            raise ValueError(
                f"AudioFile {state.get('id')} missing asr_languages - "
                f"required for speech recognition processing"
            )

        if not state.get('llm_language'):
            raise ValueError(
                f"AudioFile {state.get('id')} missing llm_language - "
                f"required for LLM processing"
            )

        if not state.get('scene'):
            raise ValueError(
                f"AudioFile {state.get('id')} missing scene - "
                f"required for processing context"
            )

        # Check basic file metadata
        file_size = state.get('file_size')
        if not file_size or file_size <= 0:
            raise ValueError(
                f"AudioFile {state.get('id')} has invalid file_size: "
                f"{file_size} - required for processing validation"
            )

        self.logger.info(
            f"AudioFile {state.get('id')} passed all critical field validations"
        )

        return state
