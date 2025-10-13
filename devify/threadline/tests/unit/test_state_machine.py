"""
Tests for unified state machine configuration and functions.

This module tests the unified state machine logic for email processing
workflows, ensuring proper state transitions and validation with the
simplified 4-state model.
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
    implementation with simplified 4-state model.
    """

    def test_email_state_transitions(self):
        """
        Test email state transitions with simplified 4-state model.

        Verifies that email status transitions follow the defined
        unified state machine rules and business logic.
        """
        # Test valid transitions from FETCHED state
        self.assertTrue(
            can_transition_to('fetched', 'processing', EMAIL_STATE_MACHINE)
        )

        # Test invalid transitions from FETCHED state
        self.assertFalse(
            can_transition_to('fetched', 'success', EMAIL_STATE_MACHINE)
        )
        self.assertFalse(
            can_transition_to('fetched', 'failed', EMAIL_STATE_MACHINE)
        )

        # Test valid transitions from PROCESSING state
        self.assertTrue(
            can_transition_to('processing', 'success', EMAIL_STATE_MACHINE)
        )
        self.assertTrue(
            can_transition_to('processing', 'failed', EMAIL_STATE_MACHINE)
        )

        # Test invalid transitions from PROCESSING state
        self.assertFalse(
            can_transition_to('processing', 'fetched', EMAIL_STATE_MACHINE)
        )

        # Test valid transitions from FAILED state (retry)
        self.assertTrue(
            can_transition_to('failed', 'processing', EMAIL_STATE_MACHINE)
        )

        # Test invalid transitions from FAILED state
        self.assertFalse(
            can_transition_to('failed', 'success', EMAIL_STATE_MACHINE)
        )
        self.assertFalse(
            can_transition_to('failed', 'fetched', EMAIL_STATE_MACHINE)
        )

        # Test that SUCCESS is terminal (no outgoing transitions)
        self.assertFalse(
            can_transition_to('success', 'processing', EMAIL_STATE_MACHINE)
        )
        self.assertFalse(
            can_transition_to('success', 'failed', EMAIL_STATE_MACHINE)
        )
        self.assertFalse(
            can_transition_to('success', 'fetched', EMAIL_STATE_MACHINE)
        )

    def test_get_next_states(self):
        """
        Test getting next possible states with simplified 4-state model.

        Verifies that the get_next_states function correctly returns
        all valid next states for given current states.
        """
        # Test next states for FETCHED
        expected_fetched_states = ['processing']
        actual_fetched_states = get_next_states('fetched', EMAIL_STATE_MACHINE)
        self.assertEqual(actual_fetched_states, expected_fetched_states)

        # Test next states for PROCESSING
        expected_processing_states = ['success', 'failed']
        actual_processing_states = get_next_states(
            'processing',
            EMAIL_STATE_MACHINE
        )
        self.assertEqual(
            set(actual_processing_states),
            set(expected_processing_states)
        )

        # Test next states for FAILED (can retry)
        expected_failed_states = ['processing']
        actual_failed_states = get_next_states('failed', EMAIL_STATE_MACHINE)
        self.assertEqual(actual_failed_states, expected_failed_states)

        # Test next states for SUCCESS (terminal state)
        expected_success_states = []
        actual_success_states = get_next_states('success', EMAIL_STATE_MACHINE)
        self.assertEqual(actual_success_states, expected_success_states)

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
            can_transition_to('invalid_status', 'processing',
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
            description = get_status_description(
                status.value,
                EMAIL_STATE_MACHINE
            )
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

    def test_workflow_path(self):
        """
        Test complete workflow paths.

        Verifies that the state machine supports expected workflow paths.
        """
        # Test success path: FETCHED -> PROCESSING -> SUCCESS
        self.assertTrue(
            can_transition_to('fetched', 'processing', EMAIL_STATE_MACHINE)
        )
        self.assertTrue(
            can_transition_to('processing', 'success', EMAIL_STATE_MACHINE)
        )

        # Test failure and retry path:
        # FETCHED -> PROCESSING -> FAILED -> PROCESSING -> SUCCESS
        self.assertTrue(
            can_transition_to('processing', 'failed', EMAIL_STATE_MACHINE)
        )
        self.assertTrue(
            can_transition_to('failed', 'processing', EMAIL_STATE_MACHINE)
        )

    def test_state_enum_values(self):
        """
        Test EmailStatus enum values.

        Verifies that the EmailStatus enum has the expected 4 states
        with correct values.
        """
        # Test that we have exactly 4 states
        self.assertEqual(len(EmailStatus), 4)

        # Test each state value
        self.assertEqual(EmailStatus.FETCHED.value, 'fetched')
        self.assertEqual(EmailStatus.PROCESSING.value, 'processing')
        self.assertEqual(EmailStatus.SUCCESS.value, 'success')
        self.assertEqual(EmailStatus.FAILED.value, 'failed')

    def test_choices_method(self):
        """
        Test EmailStatus.choices() method.

        Verifies that the choices method returns proper format
        for Django model field.
        """
        choices = EmailStatus.choices()

        # Should return a list
        self.assertIsInstance(choices, list)

        # Should have 4 choices
        self.assertEqual(len(choices), 4)

        # Each choice should be a tuple of (value, display_name)
        for choice in choices:
            self.assertIsInstance(choice, tuple)
            self.assertEqual(len(choice), 2)
            self.assertIsInstance(choice[0], str)
            self.assertIsInstance(choice[1], str)

        # Verify all expected values are present
        choice_values = [choice[0] for choice in choices]
        self.assertIn('fetched', choice_values)
        self.assertIn('processing', choice_values)
        self.assertIn('success', choice_values)
        self.assertIn('failed', choice_values)
