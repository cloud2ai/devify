"""
Tests for state machine configuration
"""

from django.test import TestCase
from jirabot.state_machine import (
    EmailStatus, AttachmentStatus,
    can_transition_attachment_to, can_transition_email_to,
    get_next_attachment_states, get_next_email_states,
    get_initial_email_status, get_initial_attachment_status,
    can_skip_ocr_for_attachment, get_attachment_processing_path
)


class StateMachineTest(TestCase):
    """Test state machine configuration and functions"""

    def test_attachment_state_transitions(self):
        """Test attachment state transitions"""
        # FETCHED -> OCR_PROCESSING should be allowed
        self.assertTrue(
            can_transition_attachment_to('fetched', 'ocr_processing')
        )

        # FETCHED -> LLM_SUCCESS should be allowed (for non-image attachments)
        self.assertTrue(
            can_transition_attachment_to('fetched', 'llm_success')
        )

        # FETCHED -> LLM_PROCESSING should not be allowed
        self.assertFalse(
            can_transition_attachment_to('fetched', 'llm_processing')
        )

        # OCR_PROCESSING -> OCR_SUCCESS should be allowed
        self.assertTrue(
            can_transition_attachment_to('ocr_processing', 'ocr_success')
        )

        # OCR_PROCESSING -> LLM_PROCESSING should not be allowed
        self.assertFalse(
            can_transition_attachment_to('ocr_processing', 'llm_processing')
        )

        # OCR_SUCCESS -> LLM_PROCESSING should be allowed
        self.assertTrue(
            can_transition_attachment_to('ocr_success', 'llm_processing')
        )

    def test_email_state_transitions(self):
        """Test email state transitions"""
        # FETCHED -> OCR_PROCESSING should be allowed
        self.assertTrue(
            can_transition_email_to('fetched', 'ocr_processing')
        )

        # FETCHED -> SUMMARY_PROCESSING should not be allowed
        self.assertFalse(
            can_transition_email_to('fetched', 'summary_processing')
        )

        # OCR_SUCCESS -> SUMMARY_PROCESSING should be allowed
        self.assertTrue(
            can_transition_email_to('ocr_success', 'summary_processing')
        )

    def test_get_next_states(self):
        """Test getting next possible states"""
        # FETCHED should have OCR_PROCESSING as next state
        next_states = get_next_email_states('fetched')
        self.assertEqual(next_states, ['ocr_processing'])

        # FETCHED should have OCR_PROCESSING and LLM_SUCCESS as next states
        next_states = get_next_attachment_states('fetched')
        self.assertIn('ocr_processing', next_states)
        self.assertIn('llm_success', next_states)

        # OCR_PROCESSING should have OCR_SUCCESS and OCR_FAILED as next states
        next_states = get_next_attachment_states('ocr_processing')
        self.assertIn('ocr_success', next_states)
        self.assertIn('ocr_failed', next_states)

        # LLM_SUCCESS should have no next states (terminal)
        next_states = get_next_attachment_states('llm_success')
        self.assertEqual(next_states, [])

    def test_initial_states(self):
        """Test initial states for new objects"""
        # Email should start with FETCHED status
        self.assertEqual(get_initial_email_status(), 'fetched')

        # Attachment should start with FETCHED status
        self.assertEqual(get_initial_attachment_status(), 'fetched')

    def test_attachment_processing_path(self):
        """Test attachment processing path logic"""
        # Mock attachment objects for testing
        class MockAttachment:
            def __init__(self, is_image):
                self.is_image = is_image

        # Test image attachment path
        image_attachment = MockAttachment(is_image=True)
        image_path = get_attachment_processing_path(image_attachment)
        expected_image_path = ['fetched', 'ocr_processing', 'ocr_success', 'llm_processing', 'llm_success']
        self.assertEqual(image_path, expected_image_path)

        # Test non-image attachment path
        non_image_attachment = MockAttachment(is_image=False)
        non_image_path = get_attachment_processing_path(non_image_attachment)
        expected_non_image_path = ['fetched', 'llm_success']
        self.assertEqual(non_image_path, expected_non_image_path)

    def test_can_skip_ocr(self):
        """Test OCR skip logic"""
        class MockAttachment:
            def __init__(self, is_image):
                self.is_image = is_image

        # Image attachments cannot skip OCR
        image_attachment = MockAttachment(is_image=True)
        self.assertFalse(can_skip_ocr_for_attachment(image_attachment))

        # Non-image attachments can skip OCR
        non_image_attachment = MockAttachment(is_image=False)
        self.assertTrue(can_skip_ocr_for_attachment(non_image_attachment))

    def test_invalid_states(self):
        """Test handling of invalid states"""
        # Invalid current status should return False
        self.assertFalse(
            can_transition_attachment_to('invalid_status', 'ocr_processing')
        )

        # Invalid target status should return False
        self.assertFalse(
            can_transition_attachment_to('fetched', 'invalid_status')
        )

        # Invalid status should return empty list for next states
        next_states = get_next_attachment_states('invalid_status')
        self.assertEqual(next_states, [])
