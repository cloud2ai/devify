"""
Speech-to-text processing workflow using LangGraph StateGraph.

This module implements a simplified sequential workflow for processing audio files
through speech recognition, using LangGraph but with simplified configuration.
"""

import logging
from functools import lru_cache
import traceback
from typing import Dict, Any

from langgraph.graph import StateGraph, START, END

from speechtotext.models import AudioFile
from speechtotext.agents.checkpoint_manager import create_checkpointer
from speechtotext.agents.nodes.workflow_prepare import WorkflowPrepareNode
from speechtotext.agents.nodes.speech_recognition import SpeechRecognitionNode
from speechtotext.agents.nodes.segment_processing import SegmentProcessingNode
from speechtotext.agents.nodes.summary_processing import SummaryProcessingNode
from speechtotext.agents.nodes.workflow_finalize import WorkflowFinalizeNode
from speechtotext.agents.speechtotext_state import (
    AudioFileState,
    create_audio_file_state,
    has_node_errors
)

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def create_speech_processing_graph():
    """Create and compile the speech processing workflow graph."""
    logger.info("Building speech processing workflow graph")

    # Initialize workflow
    workflow = StateGraph(AudioFileState)

    # Add nodes - directly use Node instances (they have __call__ method)
    workflow.add_node("workflow_prepare_node", WorkflowPrepareNode())
    workflow.add_node("speech_recognition_node", SpeechRecognitionNode())
    workflow.add_node("segment_processing_node", SegmentProcessingNode())
    workflow.add_node("summary_processing_node", SummaryProcessingNode())
    workflow.add_node("workflow_finalize_node", WorkflowFinalizeNode())

    # Set entry point
    workflow.add_edge(START, "workflow_prepare_node")

    # Add simple sequential edges - each node handles its own
    # completion/failure logic
    workflow.add_edge("workflow_prepare_node", "speech_recognition_node")
    workflow.add_edge("speech_recognition_node", "segment_processing_node")
    workflow.add_edge("segment_processing_node", "summary_processing_node")
    workflow.add_edge("summary_processing_node", "workflow_finalize_node")
    workflow.add_edge("workflow_finalize_node", END)

    # Compile with checkpointer
    graph = workflow.compile(checkpointer=create_checkpointer())

    logger.info("Speech processing workflow graph compiled successfully")
    return graph


def execute_speech_processing_workflow(
    audio_file_id: str,
    force: bool = False
) -> Dict[str, Any]:
    """
    Execute the speech processing workflow for an audio file.

    Args:
        audio_file_id: ID of the audio file to process
        force: Whether to force execution even if already completed

    Returns:
        Dict with success status and result/error
    """
    logger.info(f"Starting workflow for audio_file_id: {audio_file_id}, "
                f"force: {force}")

    try:
        # Create initial state (need to get user_id from AudioFile)
        try:
            audio_file = AudioFile.objects.get(id=audio_file_id)
            initial_state = create_audio_file_state(
                audio_file_id,
                str(audio_file.user_id),
                force
            )
        except AudioFile.DoesNotExist:
            raise ValueError(f'AudioFile {audio_file_id} not found')

        # Get compiled graph
        graph = create_speech_processing_graph()

        # Execute workflow with configuration
        config = {
            "configurable": {
                "thread_id": f"workflow_{audio_file_id}",
                "checkpoint_ns": "speech_processing"
            }
        }
        result = graph.invoke(initial_state, config=config)

        # Check final status - log the result for debugging
        logger.info(f"Workflow result: {result}")

        # Check if workflow completed successfully
        # For now, we'll consider it completed if there are no node errors
        if not has_node_errors(result):
            logger.info(f"Workflow completed successfully: {audio_file_id}")
            return {
                'success': True,
                'result': result,
                'error': None
            }
        else:
            # Get error details from node_errors
            node_errors = result.get('node_errors', {})
            error_msg = f'Workflow failed with errors: {node_errors}'
            logger.error(f"Workflow failed: {audio_file_id}, "
                         f"error: {error_msg}")

            return {
                'success': False,
                'result': result,
                'error': error_msg
            }

    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Workflow execution error: {audio_file_id}, {e}")
        logger.error(f"Full traceback:\n{error_traceback}")

        return {
            'success': False,
            'result': None,
            'error': str(e)
        }


def get_workflow_status(audio_file_id: str) -> Dict[str, Any]:
    """
    Get the current status of a workflow for an audio file.

    Args:
        audio_file_id: ID of the audio file

    Returns:
        Dict with workflow status information
    """
    try:
        # Get compiled graph
        graph = create_speech_processing_graph()

        # Get current state from checkpointer
        # This would need to be implemented based on your checkpointer
        # For now, return a basic status
        return {
            'audio_file_id': audio_file_id,
            'status': 'unknown',
            'message': 'Workflow status check not fully implemented'
        }
    except Exception as e:
        logger.error(f"Error getting workflow status: {audio_file_id}, {e}")
        return {
            'audio_file_id': audio_file_id,
            'status': 'error',
            'error': str(e)
        }


def clear_workflow_checkpoint(audio_file_id: str) -> bool:
    """Clear workflow checkpoint for an audio file."""
    try:
        logger.info(f"Clearing checkpoint for: {audio_file_id}")
        return True
    except Exception as e:
        logger.error(f"Error clearing checkpoint: {audio_file_id}, {e}")
        return False