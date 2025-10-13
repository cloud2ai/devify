"""
Workflow finalization for audio file processing.

This node handles the final atomic synchronization of all workflow
results to the database and sets the final processing status.
"""

from typing import Dict, Any

from django.db import transaction

from speechtotext.agents.nodes.base_node import BaseLangGraphNode
from speechtotext.agents.speechtotext_state import (
    AudioFileState,
    has_node_errors,
    get_all_node_names_with_errors
)
from speechtotext.models import (
    AudioFile,
    ProcessingStatus,
    AudioFileSegment
)


class WorkflowFinalizeNode(BaseLangGraphNode):
    """
    Workflow finalization node for LangGraph workflow.

    This node serves as the single exit point for all database synchronization.
    It atomically persists all workflow results and sets the final processing
    status based on whether there are any node errors.

    Responsibilities:
    - Determine workflow success/failure based on node_errors
    - Atomically sync all workflow results to database
    - Update AudioFile status to SUCCESS or FAILED
    - Handle force mode considerations
    - Ensure data consistency and integrity
    """

    def __init__(self):
        super().__init__("workflow_finalize_node")

    def can_enter_node(self, state: AudioFileState) -> bool:
        """
        Finalize node always runs to ensure proper cleanup.
        """
        return True

    def before_processing(self, state: AudioFileState) -> AudioFileState:
        """
        Pre-processing: Basic validation for finalization.

        Args:
            state (AudioFileState): Current audio file state

        Returns:
            AudioFileState: Validated state
        """
        # Validate audio_file_id exists
        audio_file_id = state.get('id')
        if not audio_file_id:
            raise ValueError('audio_file_id is required for finalization')

        # Load AudioFile to ensure it exists
        try:
            self.audio_file = AudioFile.objects.get(id=audio_file_id)
        except AudioFile.DoesNotExist:
            raise ValueError(f'AudioFile {audio_file_id} not found')

        self.logger.info(f"Starting finalization for AudioFile {audio_file_id}")
        return state

    def execute_processing(self, state: AudioFileState) -> AudioFileState:
        """
        Execute database operations and status update based on workflow results.

        1. Determine workflow success/failure based on node_errors
        2. If successful: sync data to database and set SUCCESS status
        3. If failed: only set FAILED status, no data sync
        """
        # Step 1: Determine workflow success/failure
        has_errors = has_node_errors(state)
        force = state.get('force', False)

        if has_errors:
            # Workflow failed - only update status, no data sync
            error_nodes = get_all_node_names_with_errors(state)
            node_errors = state.get('node_errors', {})
            error_summary = (
                f"Workflow failed with errors in nodes: "
                f"{list(node_errors.keys())}"
            )

            self.logger.error(
                f"Workflow failed with errors in nodes: {error_nodes}"
            )
            self.logger.info("Skipping data sync due to workflow errors")

            # Update status to FAILED (unless in force mode)
            if not force:
                self.audio_file.set_status(
                    ProcessingStatus.FAILED.value, error_message=error_summary
                )
                self.logger.info(
                    f"AudioFile {self.audio_file.id} status set to FAILED"
                )
            else:
                self.logger.info(
                    f"Force mode: skipping status update to FAILED, "
                    f"current status remains {self.audio_file.status}"
                )
        else:
            # Workflow succeeded - sync data and update status
            self.logger.info("Workflow completed successfully")

            # Step 2: Sync all data to database
            self._sync_data_to_database(state)

            # Step 3: Update status to SUCCESS (unless in force mode)
            if not force:
                self.audio_file.set_status(ProcessingStatus.SUCCESS.value)
                self.logger.info(
                    f"AudioFile {self.audio_file.id} status set to SUCCESS"
                )
            else:
                self.logger.info(
                    f"Force mode: skipping status update to SUCCESS, "
                    f"current status remains {self.audio_file.status}"
                )

        self.logger.info(
            f"Workflow finalized for AudioFile {self.audio_file.id}"
        )
        return state

    def _sync_data_to_database(self, state: AudioFileState) -> None:
        """
        Sync all workflow results to database atomically.

        This method handles all data updates but does NOT update status.
        Status updates are handled separately in execute_processing.

        Args:
            state (AudioFileState): Current audio file state
        """
        with transaction.atomic():
            audio_file = AudioFile.objects.select_for_update().get(
                id=self.audio_file.id
            )

            # Sync segments if available
            segments = state.get('segments', [])
            if segments:
                audio_file.segments.all().delete()
                segment_objects = [
                    AudioFileSegment(
                        audio_file=audio_file,
                        segment_order=seg.get('segment_order', 0),
                        start_time=seg.get('start_time', 0.0),
                        end_time=seg.get('end_time', 0.0),
                        duration=seg.get('duration', 0.0),
                        speaker=seg.get('speaker', ''),
                        text=seg.get('text', ''),
                        llm_text=seg.get('llm_text', ''),
                        llm_error=seg.get('llm_error', '')
                    )
                    for seg in segments
                ]
                AudioFileSegment.objects.bulk_create(segment_objects)
                self.logger.info(
                    f"Synced {len(segments)} segments to database"
                )

            # Sync summary if available
            summary = state.get('summary', '')
            if summary:
                audio_file.summary = summary
                self.logger.info("Synced summary to database")

            # Sync translation if available
            translation = state.get('translation', '')
            if translation:
                audio_file.translation = translation
                self.logger.info("Synced translation to database")

            # Save all changes to database
            audio_file.save()
            self.logger.info(
                f"AudioFile {self.audio_file.id} saved to database with "
                f"summary and translation updates"
            )

        self.logger.info(
            f"All data synced to database for AudioFile {self.audio_file.id}"
        )

    def _handle_error(
        self, error: Exception, state: AudioFileState
    ) -> AudioFileState:
        """
        Handle errors that occur during finalization processing.

        For finalize node, we need to ensure the database status is updated
        even if the finalization process itself fails.

        Args:
            error (Exception): The error that occurred
            state (AudioFileState): Current audio file state

        Returns:
            AudioFileState: Updated state with error information
        """
        # First, call parent's error handling to record the error
        state = super()._handle_error(error, state)

        # Then, ensure database status is set to FAILED (unless in force mode)
        force = state.get('force', False)
        if force:
            self.logger.info(
                "Force mode: skipping status update after finalization error"
            )
            return state

        try:
            # Use node_errors from state to build error message
            node_errors = state.get('node_errors', {})
            error_nodes = list(node_errors.keys())
            error_message = (
                f"Finalization failed with errors in nodes: {error_nodes}"
            )

            self.audio_file.set_status(
                ProcessingStatus.FAILED.value, error_message=error_message
            )
            self.logger.info(
                f"AudioFile {self.audio_file.id} status set to FAILED "
                f"due to finalization error"
            )
        except Exception as status_error:
            self.logger.error(
                f"Failed to update status after finalization error: "
                f"{status_error}"
            )

        return state
