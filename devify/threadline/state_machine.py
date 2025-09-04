"""
State Machine Configuration for Email Processing Workflow

This module defines the state machine rules for both EmailMessage and
EmailAttachment models, making state transitions more explicit and easier
to maintain.

Design Logic Overview:
=====================

1. Linear Processing Flow:
   - FETCHED -> OCR -> LLM_EMAIL -> LLM_SUMMARY -> ISSUE -> COMPLETED
   - Each stage must complete successfully before proceeding to the next
   - Failed stages can retry by returning to their processing state

2. Error Handling Strategy:
   - FAILED states always transition back to their respective PROCESSING state
   - This enables automatic retry without manual intervention
   - Stuck tasks are detected and reset by the scheduler

3. Parallel Processing Support:
   - Currently supports sequential processing for stability and reliability
   - Future enhancement: OCR and email content processing can run in parallel
   - Chain orchestrator manages the processing sequence and dependencies

4. Flexible Completion Paths:
   - LLM_SUMMARY_SUCCESS can proceed to either ISSUE_PROCESSING or COMPLETED
   - COMPLETED state is terminal and cannot transition to other states
   - Issue creation is optional based on user configuration

5. Success State Skipping:
   - Adjacent SUCCESS states can directly transition to the next SUCCESS state
   - This allows skipping intermediate processing stages when conditions are met
   - Example: OCR_SUCCESS can directly go to LLM_EMAIL_SUCCESS if content exists

6. State Validation:
   - All transitions are validated against the state machine rules
   - Force mode bypasses validation for manual reprocessing
   - Prevents invalid state transitions that could corrupt workflow

7. Recovery Mechanisms:
   - Automatic retry for failed processing stages
   - Timeout-based stuck task detection and reset
   - Graceful degradation when external services are unavailable

8. Monitoring and Debugging:
   - Clear state descriptions for each status
   - Comprehensive logging of state transitions
   - Easy identification of workflow bottlenecks
"""

from enum import Enum
from typing import List, Dict, Any


class EmailStatus(Enum):
    """
    Email processing status enumeration.

    Unified status for email and attachment processing workflow.
    """
    # Email fetch status
    FETCHED = 'fetched'

    # OCR processing status
    OCR_PROCESSING = 'ocr_processing'
    OCR_SUCCESS = 'ocr_success'
    OCR_FAILED = 'ocr_failed'

    # LLM OCR processing status
    LLM_OCR_PROCESSING = 'llm_ocr_processing'
    LLM_OCR_SUCCESS = 'llm_ocr_success'
    LLM_OCR_FAILED = 'llm_ocr_failed'

    # LLM email content processing status
    LLM_EMAIL_PROCESSING = 'llm_email_processing'
    LLM_EMAIL_SUCCESS = 'llm_email_success'
    LLM_EMAIL_FAILED = 'llm_email_failed'

    # LLM summary generation status
    LLM_SUMMARY_PROCESSING = 'llm_summary_processing'
    LLM_SUMMARY_SUCCESS = 'llm_summary_success'
    LLM_SUMMARY_FAILED = 'llm_summary_failed'

    # Issue creation status
    ISSUE_PROCESSING = 'issue_processing'
    ISSUE_SUCCESS = 'issue_success'
    ISSUE_FAILED = 'issue_failed'

    # Completion status
    COMPLETED = 'completed'

    @classmethod
    def choices(cls):
        """
        Return choices for Django model field.

        Returns:
            List of tuples with (value, display_name)
        """
        return [
            # Email fetch status
            (cls.FETCHED.value, 'Fetched'),

            # OCR processing status
            (cls.OCR_PROCESSING.value, 'OCR Processing'),
            (cls.OCR_SUCCESS.value, 'OCR Success'),
            (cls.OCR_FAILED.value, 'OCR Failed'),

            # LLM OCR processing status
            (cls.LLM_OCR_PROCESSING.value, 'LLM OCR Processing'),
            (cls.LLM_OCR_SUCCESS.value, 'LLM OCR Success'),
            (cls.LLM_OCR_FAILED.value, 'LLM OCR Failed'),

            # LLM email content processing status
            (cls.LLM_EMAIL_PROCESSING.value, 'LLM Email Processing'),
            (cls.LLM_EMAIL_SUCCESS.value, 'LLM Email Success'),
            (cls.LLM_EMAIL_FAILED.value, 'LLM Email Failed'),

            # LLM summary generation status
            (cls.LLM_SUMMARY_PROCESSING.value, 'LLM Summary Processing'),
            (cls.LLM_SUMMARY_SUCCESS.value, 'LLM Summary Success'),
            (cls.LLM_SUMMARY_FAILED.value, 'LLM Summary Failed'),

            # Issue creation status
            (cls.ISSUE_PROCESSING.value, 'Issue Processing'),
            (cls.ISSUE_SUCCESS.value, 'Issue Success'),
            (cls.ISSUE_FAILED.value, 'Issue Failed'),

            # Completion status
            (cls.COMPLETED.value, 'Completed')
        ]


# Unified email state machine for email and attachment processing
EMAIL_STATE_MACHINE = {
    EmailStatus.FETCHED: {
        'next': [
            EmailStatus.OCR_PROCESSING,
            EmailStatus.OCR_SUCCESS
        ],
        'description': 'Email has been fetched and ready for processing'
    },

    EmailStatus.OCR_PROCESSING: {
        'next': [
            EmailStatus.OCR_SUCCESS,
            EmailStatus.OCR_FAILED,
        ],
        'description': 'OCR processing is in progress'
    },

    EmailStatus.OCR_SUCCESS: {
        'next': [
            EmailStatus.LLM_OCR_PROCESSING,
            EmailStatus.LLM_OCR_SUCCESS
        ],
        'description': 'OCR processing completed successfully'
    },

    EmailStatus.OCR_FAILED: {
        'next': [
            EmailStatus.OCR_PROCESSING,
        ],
        'description': 'OCR processing failed'
    },

    EmailStatus.LLM_OCR_PROCESSING: {
        'next': [
            EmailStatus.LLM_OCR_SUCCESS,
            EmailStatus.LLM_OCR_FAILED,
        ],
        'description': 'LLM processing OCR results in progress'
    },

    EmailStatus.LLM_OCR_SUCCESS: {
        'next': [
            EmailStatus.LLM_EMAIL_PROCESSING,
            EmailStatus.LLM_EMAIL_SUCCESS
        ],
        'description': 'LLM OCR processing completed successfully'
    },

    EmailStatus.LLM_OCR_FAILED: {
        'next': [
            EmailStatus.LLM_OCR_PROCESSING,
        ],
        'description': 'LLM OCR processing failed'
    },

    EmailStatus.LLM_EMAIL_PROCESSING: {
        'next': [
            EmailStatus.LLM_EMAIL_SUCCESS,
            EmailStatus.LLM_EMAIL_FAILED,
        ],
        'description': 'LLM processing email content in progress'
    },

    EmailStatus.LLM_EMAIL_SUCCESS: {
        'next': [
            EmailStatus.LLM_SUMMARY_PROCESSING,
            EmailStatus.LLM_SUMMARY_SUCCESS
        ],
        'description': 'LLM email processing completed successfully'
    },

    EmailStatus.LLM_EMAIL_FAILED: {
        'next': [
            EmailStatus.LLM_EMAIL_PROCESSING,
        ],
        'description': 'LLM email processing failed'
    },

    EmailStatus.LLM_SUMMARY_PROCESSING: {
        'next': [
            EmailStatus.LLM_SUMMARY_SUCCESS,
            EmailStatus.LLM_SUMMARY_FAILED,
        ],
        'description': 'LLM summary generation in progress'
    },

    EmailStatus.LLM_SUMMARY_SUCCESS: {
        'next': [
            EmailStatus.ISSUE_PROCESSING,
            EmailStatus.ISSUE_SUCCESS,
            EmailStatus.COMPLETED
        ],
        'description': 'LLM summary generation completed successfully'
    },

    EmailStatus.LLM_SUMMARY_FAILED: {
        'next': [
            EmailStatus.LLM_SUMMARY_PROCESSING,
        ],
        'description': 'LLM summary generation failed'
    },

    EmailStatus.ISSUE_PROCESSING: {
        'next': [
            EmailStatus.ISSUE_SUCCESS,
            EmailStatus.ISSUE_FAILED,
            EmailStatus.COMPLETED,  # Allow direct completion when no issue needed
        ],
        'description': 'Issue creation is in progress or skipped'
    },

    EmailStatus.ISSUE_SUCCESS: {
        'next': [
            EmailStatus.COMPLETED,
        ],
        'description': 'Issue creation completed successfully'
    },

    EmailStatus.ISSUE_FAILED: {
        'next': [
            EmailStatus.ISSUE_PROCESSING,
        ],
        'description': 'Issue creation failed'
    },

    EmailStatus.COMPLETED: {
        'next': [],
        'description': 'Email processing completed successfully'
    }
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


def get_next_states(current_status: str, state_machine: Dict) -> List[str]:
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
