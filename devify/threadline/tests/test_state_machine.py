"""
Tests for unified state machine configuration and functions.

This module tests the unified state machine logic for email processing
workflows, ensuring proper state transitions and validation.
"""

from django.test import TestCase

from threadline.state_machine import (
    EmailStatus,
    can_transition_to,
    get_next_states,
    get_status_description,
    get_initial_email_status,
    EMAIL_STATE_MACHINE
)


class StateMachineTest(TestCase):
    """
    Test unified state machine configuration and functions.

    This class provides comprehensive testing for the unified state machine
    implementation, covering email and attachment processing workflows.
    """

    def test_email_state_transitions(self):
        """
        Test email state transitions.

        Verifies that email status transitions follow the defined
        unified state machine rules and business logic.
        """
        # Test valid transitions from FETCHED state
        self.assertTrue(
            can_transition_to('fetched', 'ocr_processing',
                            EMAIL_STATE_MACHINE)
        )
        self.assertTrue(
            can_transition_to('fetched', 'ocr_success',
                            EMAIL_STATE_MACHINE)
        )

        # Test invalid transitions from FETCHED state
        self.assertFalse(
            can_transition_to('fetched', 'llm_summary_processing',
                            EMAIL_STATE_MACHINE)
        )

        # Test valid transitions from OCR_SUCCESS state
        self.assertTrue(
            can_transition_to('ocr_success', 'llm_ocr_processing',
                            EMAIL_STATE_MACHINE)
        )
        # OCR_SUCCESS can only transition to LLM_OCR_PROCESSING in linear flow
        self.assertFalse(
            can_transition_to('ocr_success', 'llm_email_processing',
                            EMAIL_STATE_MACHINE)
        )
        self.assertFalse(
            can_transition_to('ocr_success', 'llm_summary_processing',
                            EMAIL_STATE_MACHINE)
        )

        # Test valid transitions from LLM_OCR_SUCCESS state
        self.assertTrue(
            can_transition_to('llm_ocr_success', 'llm_email_processing',
                            EMAIL_STATE_MACHINE)
        )
        # LLM_OCR_SUCCESS can only transition to LLM_EMAIL_PROCESSING in linear flow
        self.assertFalse(
            can_transition_to('llm_ocr_success', 'llm_summary_processing',
                            EMAIL_STATE_MACHINE)
        )

        # Test valid transitions from LLM_EMAIL_SUCCESS state
        self.assertTrue(
            can_transition_to('llm_email_success', 'llm_summary_processing',
                            EMAIL_STATE_MACHINE)
        )
        # LLM_EMAIL_SUCCESS can only transition to LLM_SUMMARY_PROCESSING in linear flow
        self.assertFalse(
            can_transition_to('llm_email_success', 'issue_processing',
                            EMAIL_STATE_MACHINE)
        )

        # Test valid transitions from LLM_SUMMARY_SUCCESS state
        self.assertTrue(
            can_transition_to('llm_summary_success', 'issue_processing',
                            EMAIL_STATE_MACHINE)
        )
        self.assertTrue(
            can_transition_to('llm_summary_success', 'completed',
                            EMAIL_STATE_MACHINE)
        )

        # Test valid transitions from ISSUE_SUCCESS state
        self.assertTrue(
            can_transition_to('issue_success', 'completed',
                            EMAIL_STATE_MACHINE)
        )
        # ISSUE_SUCCESS can only transition to COMPLETED (terminal state)
        self.assertFalse(
            can_transition_to('issue_success', 'fetched',
                            EMAIL_STATE_MACHINE)
        )

    def test_get_next_states(self):
        """
        Test getting next possible states.

        Verifies that the get_next_states function correctly returns
        all valid next states for given current states.
        """
        # Test next states for FETCHED
        expected_fetched_states = ['ocr_processing', 'ocr_success']
        actual_fetched_states = get_next_states('fetched', EMAIL_STATE_MACHINE)
        self.assertEqual(actual_fetched_states, expected_fetched_states)

        # Test next states for OCR_PROCESSING
        expected_ocr_processing_states = ['ocr_success', 'ocr_failed']
        actual_ocr_processing_states = get_next_states('ocr_processing',
                                                     EMAIL_STATE_MACHINE)
        self.assertEqual(actual_ocr_processing_states, expected_ocr_processing_states)

        # Test next states for OCR_SUCCESS
        expected_ocr_success_states = ['llm_ocr_processing', 'llm_ocr_success']
        actual_ocr_success_states = get_next_states('ocr_success',
                                                 EMAIL_STATE_MACHINE)
        self.assertEqual(actual_ocr_success_states, expected_ocr_success_states)

        # Test next states for COMPLETED
        expected_completed_states = []
        actual_completed_states = get_next_states('completed', EMAIL_STATE_MACHINE)
        self.assertEqual(actual_completed_states, expected_completed_states)

    def test_initial_states(self):
        """
        Test initial states for new objects.

        Verifies that newly created email objects start with
        the correct initial status.
        """
        # Test initial email status
        expected_email_status = 'fetched'
        actual_email_status = get_initial_email_status()
        self.assertEqual(actual_email_status, expected_email_status)

    def test_invalid_states(self):
        """
        Test handling of invalid states.

        Verifies that the state machine functions gracefully handle
        invalid or unknown status values.
        """
        # Test invalid current status
        self.assertFalse(
            can_transition_to('invalid_status', 'ocr_processing',
                            EMAIL_STATE_MACHINE)
        )

        # Test invalid target status
        self.assertFalse(
            can_transition_to('fetched', 'invalid_status',
                            EMAIL_STATE_MACHINE)
        )

        # Test invalid status in get_next_states
        expected_empty_list = []
        actual_next_states = get_next_states('invalid_status',
                                           EMAIL_STATE_MACHINE)
        self.assertEqual(actual_next_states, expected_empty_list)

    def test_state_descriptions(self):
        """
        Test state descriptions.

        Verifies that all states have meaningful descriptions.
        """
        # Test that all states have descriptions
        for status in EmailStatus:
            description = get_status_description(status.value, EMAIL_STATE_MACHINE)
            self.assertNotEqual(description, "Unknown status")
            self.assertIsInstance(description, str)
            self.assertGreater(len(description), 0)

    def test_state_machine_completeness(self):
        """
        Test state machine completeness.

        Verifies that all EmailStatus values are defined in the state machine
        and have proper next state definitions.
        """
        # Test that all EmailStatus values are in the state machine
        for status in EmailStatus:
            self.assertIn(status, EMAIL_STATE_MACHINE)

            # Test that each state has next states defined
            state_info = EMAIL_STATE_MACHINE[status]
            self.assertIn('next', state_info)
            self.assertIn('description', state_info)

            # Test that next states are valid EmailStatus values
            for next_state in state_info['next']:
                self.assertIn(next_state, EmailStatus)
