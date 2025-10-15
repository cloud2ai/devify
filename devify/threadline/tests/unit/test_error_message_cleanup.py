"""
Tests for error_message cleanup when transitioning to SUCCESS status.

This module tests that error messages are automatically cleared when
emails transition to SUCCESS status, ensuring a clean state.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model

from threadline.models import EmailMessage, EmailTask
from threadline.state_machine import EmailStatus

User = get_user_model()


class ErrorMessageCleanupTest(TestCase):
    """
    Test error_message cleanup functionality.

    Verifies that error messages are automatically cleared when
    transitioning to SUCCESS status.
    """

    def setUp(self):
        """
        Set up test data.
        """
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.email_task = EmailTask.objects.create(
            task_type=EmailTask.TaskType.IMAP_FETCH,
            status=EmailTask.TaskStatus.COMPLETED,
        )

        self.email = EmailMessage.objects.create(
            user=self.user,
            message_id='test-message-id',
            subject='Test Subject',
            sender='sender@example.com',
            recipients='recipient@example.com',
            received_at='2024-01-01T00:00:00Z',
            raw_content='Test content',
            status=EmailStatus.FETCHED.value,
            error_message=''
        )

    def test_error_message_cleared_on_success(self):
        """
        Test that error_message is cleared when transitioning to SUCCESS.
        """
        # Follow valid state transitions: FETCHED -> PROCESSING -> FAILED
        self.email.set_status(EmailStatus.PROCESSING.value)
        self.email.set_status(
            EmailStatus.FAILED.value,
            error_message='Processing failed due to timeout'
        )
        self.email.refresh_from_db()
        self.assertEqual(self.email.status, EmailStatus.FAILED.value)
        self.assertEqual(
            self.email.error_message,
            'Processing failed due to timeout'
        )

        # Retry: FAILED -> PROCESSING -> SUCCESS
        self.email.set_status(EmailStatus.PROCESSING.value)
        self.email.set_status(EmailStatus.SUCCESS.value)
        self.email.refresh_from_db()

        # Verify error_message is cleared
        self.assertEqual(self.email.status, EmailStatus.SUCCESS.value)
        self.assertEqual(self.email.error_message, '')

    def test_error_message_cleared_on_retry_success(self):
        """
        Test that error_message is cleared after retry succeeds.

        This simulates a common scenario where:
        1. Email fails with error message
        2. User retries
        3. Email succeeds
        Error message should be cleared in step 3.
        """
        # Initial processing fails
        self.email.status = EmailStatus.PROCESSING.value
        self.email.save()

        self.email.set_status(
            EmailStatus.FAILED.value,
            error_message='LLM API timeout'
        )
        self.email.refresh_from_db()
        self.assertNotEqual(self.email.error_message, '')

        # Retry: FAILED -> PROCESSING
        self.email.status = EmailStatus.PROCESSING.value
        self.email.save()

        # Success on retry
        self.email.set_status(EmailStatus.SUCCESS.value)
        self.email.refresh_from_db()

        # Error message should be cleared
        self.assertEqual(self.email.status, EmailStatus.SUCCESS.value)
        self.assertEqual(self.email.error_message, '')

    def test_error_message_not_cleared_on_failed(self):
        """
        Test that error_message is NOT cleared when transitioning to FAILED.
        """
        # Follow valid transitions: FETCHED -> PROCESSING -> FAILED
        self.email.set_status(EmailStatus.PROCESSING.value)
        self.email.set_status(
            EmailStatus.FAILED.value,
            error_message='First error'
        )
        self.email.refresh_from_db()
        self.assertEqual(self.email.error_message, 'First error')

        # Retry and fail again: FAILED -> PROCESSING -> FAILED
        self.email.set_status(EmailStatus.PROCESSING.value)
        self.email.set_status(
            EmailStatus.FAILED.value,
            error_message='Second error'
        )
        self.email.refresh_from_db()

        # Error message should be updated, not cleared
        self.assertEqual(self.email.error_message, 'Second error')

    def test_error_message_not_cleared_on_processing(self):
        """
        Test that error_message is preserved when transitioning to PROCESSING.
        """
        # Follow valid transitions: FETCHED -> PROCESSING -> FAILED
        self.email.set_status(EmailStatus.PROCESSING.value)
        self.email.set_status(
            EmailStatus.FAILED.value,
            error_message='Original error'
        )
        self.email.refresh_from_db()
        original_error = self.email.error_message

        # Transition to PROCESSING (retry)
        self.email.set_status(EmailStatus.PROCESSING.value)
        self.email.refresh_from_db()

        # Error message should be preserved
        self.assertEqual(self.email.error_message, original_error)

    def test_direct_save_does_not_clear_error_on_success(self):
        """
        Test that directly saving with status=SUCCESS doesn't clear error.

        Only set_status() method should clear error messages.
        """
        # Follow valid transitions to get to PROCESSING state
        self.email.set_status(EmailStatus.PROCESSING.value)

        # Set error message directly
        self.email.error_message = 'Test error'
        self.email.save(update_fields=['error_message'])
        self.email.refresh_from_db()
        self.assertEqual(self.email.error_message, 'Test error')

        # Directly update status to SUCCESS without using set_status()
        # (bypassing state validation for this test)
        self.email.status = EmailStatus.SUCCESS.value
        self.email.save(update_fields=['status'])
        self.email.refresh_from_db()

        # Error message should NOT be cleared (only set_status clears it)
        self.assertEqual(self.email.error_message, 'Test error')
