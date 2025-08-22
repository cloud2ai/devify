"""
Tests for OCR handling with empty content scenarios.
"""
import pytest
from django.test import TestCase
from unittest.mock import patch, MagicMock

from jirabot.models import EmailMessage, EmailAttachment, User
from jirabot.tasks.ocr import ocr_images_for_email
from jirabot.tasks.llm_attachment import organize_attachments_ocr_task
from jirabot.tasks.llm_summary import summarize_email_task


class OCREmptyContentTestCase(TestCase):
    """
    Test cases for handling OCR empty content scenarios.
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

        self.email_task = self.user.email_tasks.create(
            status='completed'
        )

        self.email = EmailMessage.objects.create(
            user=self.user,
            task=self.email_task,
            message_id='test-message-123',
            subject='Test Email with Images',
            sender='sender@example.com',
            recipients='recipient@example.com',
            received_at='2024-01-01T10:00:00Z',
            raw_content='Test email content',
            status='fetched'
        )

        # Create test attachments
        self.attachment_with_content = EmailAttachment.objects.create(
            user=self.user,
            email_message=self.email,
            filename='image_with_text.jpg',
            content_type='image/jpeg',
            file_size=1024,
            file_path='/path/to/image_with_text.jpg',
            is_image=True
        )

        self.attachment_empty_content = EmailAttachment.objects.create(
            user=self.user,
            email_message=self.email,
            filename='image_no_text.jpg',
            content_type='image/jpeg',
            file_size=1024,
            file_path='/path/to/image_no_text.jpg',
            is_image=True
        )

    @patch('jirabot.tasks.ocr.OCRHandler')
    def test_ocr_handles_empty_content(self, mock_ocr_handler):
        """
        Test that OCR task handles empty content correctly.
        """
        # Mock OCR handler to return empty content for one attachment
        mock_handler = MagicMock()
        mock_handler.recognize.side_effect = lambda file_path: (
            "Some text content" if "with_text" in file_path else ""
        )
        mock_ocr_handler.return_value = mock_handler

        # Run OCR task
        ocr_images_for_email(self.email.id)

        # Refresh from database
        self.email.refresh_from_db()
        self.attachment_with_content.refresh_from_db()
        self.attachment_empty_content.refresh_from_db()

        # Verify results
        self.assertEqual(self.email.status, 'ocr_success')
        self.assertEqual(self.attachment_with_content.ocr_content,
                        "Some text content")
        self.assertEqual(self.attachment_empty_content.ocr_content, "")

    @patch('jirabot.tasks.llm_attachment.call_llm')
    def test_summary_skips_empty_ocr_content(self, mock_call_llm):
        """
        Test that summary task skips attachments with empty OCR content.
        """
        # Set up OCR content
        self.attachment_with_content.ocr_content = "Some OCR text"
        self.attachment_with_content.save()

        self.attachment_empty_content.ocr_content = ""
        self.attachment_empty_content.save()

        # Mock LLM call
        mock_call_llm.return_value = "Processed OCR content"

        # Run summary task
        organize_attachments_ocr_task(self.email.id, force=False)

        # Refresh from database
        self.attachment_with_content.refresh_from_db()
        self.attachment_empty_content.refresh_from_db()

        # Verify only attachment with content was processed
        self.assertEqual(self.attachment_with_content.llm_content,
                        "Processed OCR content")
        self.assertIsNone(self.attachment_empty_content.llm_content)

        # Verify LLM was only called once (for the attachment with content)
        self.assertEqual(mock_call_llm.call_count, 1)

    @patch('jirabot.tasks.llm_summary.call_llm')
    def test_summarize_email_includes_only_valid_attachments(self, mock_call_llm):
        """
        Test that email summarization only includes attachments with LLM content.
        """
        # Set up email and attachment content
        self.email.llm_content = "Email content"
        self.email.save()

        self.attachment_with_content.llm_content = "Attachment LLM content"
        self.attachment_with_content.save()

        self.attachment_empty_content.llm_content = ""
        self.attachment_empty_content.save()

        # Mock LLM calls
        mock_call_llm.return_value = "Generated summary"

        # Run summarization
        summarize_email_task(self.email.id, force=False)

        # Verify LLM was called with content that includes attachment
        call_args = mock_call_llm.call_args_list
        self.assertGreater(len(call_args), 0)

        # Check that the content includes the attachment with LLM content
        for args, kwargs in call_args:
            content = args[1] if len(args) > 1 else ""
            if "image_with_text.jpg" in content:
                self.assertIn("Attachment LLM content", content)
                self.assertNotIn("image_no_text.jpg", content)