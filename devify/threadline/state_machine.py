"""
State Machine Configuration for Email Processing Workflow

This module defines the state machine rules for both EmailMessage and
EmailAttachment models, making state transitions more explicit and easier
to maintain.
"""

from enum import Enum
from typing import Dict, List, Set


class EmailStatus(Enum):
    """Email processing status enumeration"""
    FETCHED = 'fetched'
    OCR_PROCESSING = 'ocr_processing'
    OCR_SUCCESS = 'ocr_success'
    OCR_FAILED = 'ocr_failed'
    SUMMARY_PROCESSING = 'summary_processing'
    SUMMARY_SUCCESS = 'summary_success'
    SUMMARY_FAILED = 'summary_failed'
    JIRA_PROCESSING = 'jira_processing'
    JIRA_SUCCESS = 'jira_success'
    JIRA_FAILED = 'jira_failed'


class AttachmentStatus(Enum):
    """Attachment processing status enumeration"""
    FETCHED = 'fetched'  # Fetched from email
    OCR_PROCESSING = 'ocr_processing'
    OCR_SUCCESS = 'ocr_success'
    OCR_FAILED = 'ocr_failed'
    LLM_PROCESSING = 'llm_processing'
    LLM_SUCCESS = 'llm_success'
    LLM_FAILED = 'llm_failed'


# Email state machine rules
EMAIL_STATE_MACHINE = {
    EmailStatus.FETCHED: {
        'next': [EmailStatus.OCR_PROCESSING],
        'description': 'Email has been fetched and is ready for OCR'
    },
    EmailStatus.OCR_PROCESSING: {
        'next': [EmailStatus.OCR_SUCCESS, EmailStatus.OCR_FAILED],
        'description': 'OCR processing is in progress'
    },
    EmailStatus.OCR_SUCCESS: {
        'next': [EmailStatus.SUMMARY_PROCESSING],
        'description': 'OCR processing completed successfully'
    },
    EmailStatus.OCR_FAILED: {
        'next': [EmailStatus.OCR_PROCESSING],  # Can retry
        'description': 'OCR processing failed'
    },
    EmailStatus.SUMMARY_PROCESSING: {
        'next': [EmailStatus.SUMMARY_SUCCESS, EmailStatus.SUMMARY_FAILED],
        'description': 'LLM summary processing is in progress'
    },
    EmailStatus.SUMMARY_SUCCESS: {
        'next': [EmailStatus.JIRA_PROCESSING],
        'description': 'LLM summary processing completed successfully'
    },
    EmailStatus.SUMMARY_FAILED: {
        'next': [EmailStatus.SUMMARY_PROCESSING],  # Can retry
        'description': 'LLM summary processing failed'
    },
    EmailStatus.JIRA_PROCESSING: {
        'next': [EmailStatus.JIRA_SUCCESS, EmailStatus.JIRA_FAILED],
        'description': 'JIRA issue creation is in progress'
    },
    EmailStatus.JIRA_SUCCESS: {
        'next': [],  # Terminal state
        'description': 'JIRA issue creation completed successfully'
    },
    EmailStatus.JIRA_FAILED: {
        'next': [EmailStatus.JIRA_PROCESSING],  # Can retry
        'description': 'JIRA issue creation failed'
    }
}


# Attachment state machine rules
ATTACHMENT_STATE_MACHINE = {
    AttachmentStatus.FETCHED: {
        'next': [AttachmentStatus.OCR_PROCESSING, AttachmentStatus.LLM_SUCCESS],
        'description': 'Attachment has been fetched from email'
    },
    AttachmentStatus.OCR_PROCESSING: {
        'next': [AttachmentStatus.OCR_SUCCESS, AttachmentStatus.OCR_FAILED],
        'description': 'OCR processing is in progress'
    },
    AttachmentStatus.OCR_SUCCESS: {
        'next': [AttachmentStatus.LLM_PROCESSING],
        'description': 'OCR processing completed successfully'
    },
    AttachmentStatus.OCR_FAILED: {
        'next': [AttachmentStatus.OCR_PROCESSING],  # Can retry
        'description': 'OCR processing failed'
    },
    AttachmentStatus.LLM_PROCESSING: {
        'next': [AttachmentStatus.LLM_SUCCESS, AttachmentStatus.LLM_FAILED],
        'description': 'LLM processing is in progress'
    },
    AttachmentStatus.LLM_SUCCESS: {
        'next': [],  # Terminal state
        'description': 'LLM processing completed successfully'
    },
    AttachmentStatus.LLM_FAILED: {
        'next': [AttachmentStatus.LLM_PROCESSING],  # Can retry
        'description': 'LLM processing failed'
    }
}


def can_transition_to(current_status: str, target_status: str,
                     state_machine: Dict) -> bool:
    """
    Check if a status transition is allowed.

    Args:
        current_status: Current status string
        target_status: Target status string
        state_machine: State machine configuration

    Returns:
        bool: True if transition is allowed
    """
    try:
        current_enum = next(
            status for status in state_machine.keys()
            if status.value == current_status
        )
        target_enum = next(
            status for status in state_machine.keys()
            if status.value == target_status
        )

        return target_enum in state_machine[current_enum]['next']
    except StopIteration:
        return False


def get_next_states(current_status: str, state_machine: Dict) -> List[str]:
    """
    Get all possible next states for a given status.

    Args:
        current_status: Current status string
        state_machine: State machine configuration

    Returns:
        List[str]: List of possible next status values
    """
    try:
        current_enum = next(
            status for status in state_machine.keys()
            if status.value == current_status
        )
        return [status.value for status in state_machine[current_enum]['next']]
    except StopIteration:
        return []


def get_status_description(status: str, state_machine: Dict) -> str:
    """
    Get description for a given status.

    Args:
        status: Current status string
        state_machine: State machine configuration

    Returns:
        str: Status description
    """
    try:
        status_enum = next(
            s for s in state_machine.keys()
            if s.value == status
        )
        return state_machine[status_enum]['description']
    except StopIteration:
        return 'Unknown status'


# Convenience functions for specific state machines
def can_transition_email_to(current_status: str,
                            target_status: str) -> bool:
    """Check if email status transition is allowed"""
    return can_transition_to(
        current_status, target_status, EMAIL_STATE_MACHINE)


def can_transition_attachment_to(current_status: str,
                                 target_status: str) -> bool:
    """Check if attachment status transition is allowed"""
    return can_transition_to(
        current_status, target_status, ATTACHMENT_STATE_MACHINE)


def get_next_email_states(current_status: str) -> List[str]:
    """Get next possible email states"""
    return get_next_states(current_status, EMAIL_STATE_MACHINE)


def get_next_attachment_states(current_status: str) -> List[str]:
    """Get next possible attachment states"""
    return get_next_states(current_status, ATTACHMENT_STATE_MACHINE)


def get_initial_email_status() -> str:
    """Get the initial status for newly created emails"""
    return EmailStatus.FETCHED.value


def get_initial_attachment_status() -> str:
    """Get the initial status for newly created attachments"""
    return AttachmentStatus.FETCHED.value


def can_skip_ocr_for_attachment(attachment) -> bool:
    """
    Check if attachment can skip OCR processing.

    Args:
        attachment: EmailAttachment instance

    Returns:
        bool: True if OCR can be skipped
    """
    # Non-image attachments can skip OCR
    return not attachment.is_image


def get_attachment_processing_path(attachment) -> List[str]:
    """
    Get the processing path for an attachment.

    Args:
        attachment: EmailAttachment instance

    Returns:
        List[str]: List of statuses in processing order
    """
    if attachment.is_image:
        # Image attachments: FETCHED -> OCR_PROCESSING -> OCR_SUCCESS ->
        #                    LLM_PROCESSING -> LLM_SUCCESS
        return [
            AttachmentStatus.FETCHED.value,
            AttachmentStatus.OCR_PROCESSING.value,
            AttachmentStatus.OCR_SUCCESS.value,
            AttachmentStatus.LLM_PROCESSING.value,
            AttachmentStatus.LLM_SUCCESS.value
        ]
    else:
        # Non-image attachments: FETCHED -> LLM_SUCCESS (skip OCR)
        return [
            AttachmentStatus.FETCHED.value,
            AttachmentStatus.LLM_SUCCESS.value
        ]
