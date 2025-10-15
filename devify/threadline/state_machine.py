"""
State Machine Configuration for Email Processing Workflow

This module defines the state machine rules for EmailMessage models.

SIMPLIFIED STATE MACHINE (LangGraph-based)
===========================================

This state machine has been simplified from 19 states to 4 states
to align with the LangGraph architecture.

States:
-------
- FETCHED: Email has been fetched and ready for processing
- PROCESSING: Email is being processed through the workflow
- FAILED: Processing failed, can be retried
- SUCCESS: All processing completed successfully (terminal state)

State Transitions:
-----------------
FETCHED → PROCESSING (chain orchestrator starts processing)
FETCHED → FAILED (stuck or unable to start processing)
PROCESSING → SUCCESS (all tasks succeed)
PROCESSING → FAILED (any task fails)
FAILED → PROCESSING (retry)

Key Design Principles:
---------------------
1. Database status shows overall progress only
   (not individual step status)
2. Detailed step-by-step progress is managed by
   LangGraph internal state
3. Error details are logged, not reflected in status
4. Simpler state model = easier debugging, monitoring,
   and maintenance
5. Individual tasks (OCR, LLM, etc.) focus on business logic,
   not status management
6. SUCCESS is the terminal state; error_message is cleared
   on success transitions

Migration from Old States:
-------------------------
Old detailed states have been migrated to simplified states:
- All *_PROCESSING states → PROCESSING
- All *_SUCCESS states → SUCCESS
- All *_FAILED states → FAILED
- FETCHED remains unchanged
- COMPLETED has been removed (SUCCESS is now terminal)

See migration file: 0007_migrate_to_simplified_statuses.py
"""

from enum import Enum
from typing import List, Dict, Any


class EmailStatus(Enum):
    """
    Email processing status enumeration.

    Simplified status for LangGraph-based email processing workflow.

    This enum has been simplified from 19 states to 4 states:
    - FETCHED: Email has been fetched and ready for processing
    - PROCESSING: Email is being processed through the workflow
    - SUCCESS: All processing completed successfully (terminal state)
    - FAILED: Processing failed, can be retried

    Detailed progress tracking is handled by LangGraph internal state,
    not stored in the database.
    """
    # Initial state
    FETCHED = 'fetched'

    # Processing states
    PROCESSING = 'processing'
    SUCCESS = 'success'
    FAILED = 'failed'

    @classmethod
    def choices(cls):
        """
        Return choices for Django model field.

        Returns:
            List of tuples with (value, display_name)
        """
        return [
            (cls.FETCHED.value, 'Fetched'),
            (cls.PROCESSING.value, 'Processing'),
            (cls.SUCCESS.value, 'Success'),
            (cls.FAILED.value, 'Failed'),
        ]

# Email state machine - simplified for LangGraph workflow
EMAIL_STATE_MACHINE = {
    EmailStatus.FETCHED: {
        'next': [
            EmailStatus.PROCESSING,
            EmailStatus.FAILED,
        ],
        'description': 'Email has been fetched and ready for processing'
    },

    EmailStatus.PROCESSING: {
        'next': [
            EmailStatus.SUCCESS,
            EmailStatus.FAILED,
        ],
        'description': 'Email is being processed by the workflow'
    },

    EmailStatus.FAILED: {
        'next': [
            EmailStatus.PROCESSING,
        ],
        'description': 'Email processing failed, can be retried'
    },

    EmailStatus.SUCCESS: {
        'next': [],
        'description': (
            'Email processing completed successfully (terminal state)'
        )
    },
}

def can_transition_to(current_status: str, target_status: str,
                     state_machine: Dict) -> bool:
    """
    Check if status transition is allowed.

    Args:
        current_status: Current status string
        target_status: Target status string
        state_machine: State machine dictionary

    Returns:
        bool: True if transition is allowed, False otherwise
    """
    current_enum = None
    target_enum = None

    for status in EmailStatus:
        if status.value == current_status:
            current_enum = status
        if status.value == target_status:
            target_enum = status

    if current_enum not in state_machine:
        return False

    allowed_next = state_machine[current_enum]['next']
    return target_enum in allowed_next

def get_next_states(
    current_status: str,
    state_machine: Dict
) -> List[str]:
    """
    Get all possible next states for current status.

    Args:
        current_status: Current status string
        state_machine: State machine dictionary

    Returns:
        List[str]: List of possible next status values
    """
    current_enum = None

    for status in EmailStatus:
        if status.value == current_status:
            current_enum = status
            break

    if current_enum not in state_machine:
        return []

    return [state.value for state in state_machine[current_enum]['next']]

def get_status_description(status: str, state_machine: Dict) -> str:
    """
    Get description for status.

    Args:
        status: Status string
        state_machine: State machine dictionary

    Returns:
        str: Description of the status
    """
    current_enum = None

    for status_enum in EmailStatus:
        if status_enum.value == status:
            current_enum = status_enum
            break

    if current_enum not in state_machine:
        return "Unknown status"

    return state_machine[current_enum]['description']

def get_initial_email_status() -> str:
    """
    Get the initial status for newly created emails.

    Returns:
        str: Initial status value
    """
    return EmailStatus.FETCHED.value
