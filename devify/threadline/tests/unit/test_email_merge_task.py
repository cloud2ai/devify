"""
Unit tests for email merge coordination tasks.
"""

from uuid import uuid4
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from threadline.models import EmailMessage


class EmailMergeTaskTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="merge-test-user",
            email="merge-test@example.com",
            password="password123",
        )

    def _create_email(self, **kwargs) -> EmailMessage:
        defaults = {
            "user": self.user,
            "message_id": kwargs.pop(
                "message_id", f"<{uuid4().hex}@example.com>"
            ),
            "subject": kwargs.pop("subject", "Merge test"),
            "sender": kwargs.pop("sender", "sender@example.com"),
            "recipients": kwargs.pop("recipients", "recipient@example.com"),
            "received_at": kwargs.pop("received_at", timezone.now()),
            "text_content": kwargs.pop("text_content", "Hello world"),
            "html_content": kwargs.pop("html_content", ""),
            "status": kwargs.pop("status", "success"),
        }
        defaults.update(kwargs)
        return EmailMessage.objects.create(**defaults)

    @patch("threadline.tasks.email_workflow.process_email_workflow.delay")
    def test_workflow_keeps_current_email(self, mock_workflow_delay):
        email = self._create_email(message_id="<child2@example.com>")
        from threadline.tasks.email_workflow import process_email_workflow

        result = process_email_workflow(str(email.id), force=False)

        assert result == str(email.id)
        mock_workflow_delay.assert_not_called()
