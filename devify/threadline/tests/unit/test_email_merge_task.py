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

    @patch("threadline.tasks.email_merge.process_email_workflow.delay")
    @patch("threadline.tasks.email_merge.TaskTracer")
    @patch("threadline.tasks.email_merge.EmailMergeService")
    def test_process_email_merge_schedules_original_workflow(
        self,
        mock_service_class,
        mock_tracer_class,
        mock_workflow_delay,
    ):
        email = self._create_email(message_id="<child@example.com>")
        canonical = self._create_email(
            message_id="<canonical@example.com>",
            subject="Canonical merge target",
        )

        mock_service = Mock()
        mock_service.reconcile.return_value = (
            canonical,
            Mock(
                should_merge=True,
                reason=EmailMessage.MergeReason.TEXT_SIMILARITY.value,
                sources=(email,),
            ),
        )
        mock_service_class.return_value = mock_service

        tracer = Mock()
        tracer.context_summary.return_value = "EMAIL_MERGE"
        mock_tracer_class.return_value = tracer

        from threadline.tasks.email_merge import process_email_merge

        result = process_email_merge(str(email.id), force=True)

        assert result == str(email.id)
        mock_service.reconcile.assert_called_once()
        mock_workflow_delay.assert_called_once_with(
            str(email.id),
            force=True,
            language=None,
            scene=None,
        )
        tracer.create_task.assert_called_once()
        tracer.complete_task.assert_called_once()
        canonical.refresh_from_db()
        email.refresh_from_db()
        assert canonical.merged_into_id is None
        assert email.merged_into_id is None

    @patch("threadline.tasks.email_merge.process_email_workflow.delay")
    @patch("threadline.tasks.email_merge.TaskTracer")
    @patch("threadline.tasks.email_merge.EmailMergeService")
    def test_process_email_merge_marks_skipped_when_no_merge_needed(
        self,
        mock_service_class,
        mock_tracer_class,
        mock_workflow_delay,
    ):
        email = self._create_email(
            message_id="<standalone@example.com>",
            status="processing",
        )

        mock_service = Mock()
        mock_service.reconcile.return_value = (
            email,
            Mock(
                should_merge=False,
                reason="",
                sources=(),
            ),
        )
        mock_service_class.return_value = mock_service

        tracer = Mock()
        tracer.context_summary.return_value = "EMAIL_MERGE"
        mock_tracer_class.return_value = tracer

        from threadline.tasks.email_merge import process_email_merge

        result = process_email_merge(str(email.id), force=False)

        assert result == str(email.id)
        mock_workflow_delay.assert_called_once_with(
            str(email.id),
            force=False,
            language=None,
            scene=None,
        )
        email.refresh_from_db()
        assert email.merged_into_id is None
        tracer.complete_task.assert_called_once()

    @patch("threadline.tasks.email_merge.process_email_workflow.delay")
    @patch("threadline.tasks.email_merge.TaskTracer")
    @patch("threadline.tasks.email_merge.EmailMergeService")
    def test_process_email_merge_skips_auto_merge_for_manual_canonical(
        self,
        mock_service_class,
        mock_tracer_class,
        mock_workflow_delay,
    ):
        email = self._create_email(
            message_id="<manual-canonical@example.com>",
            status="processing",
            metadata={
                "manual_merge": {
                    "source_count": 2,
                    "source_ids": [1, 2],
                    "source_uuids": ["a", "b"],
                    "merged_at": timezone.now().isoformat(),
                }
            },
        )

        tracer = Mock()
        tracer.context_summary.return_value = "EMAIL_MERGE"
        mock_tracer_class.return_value = tracer

        from threadline.tasks.email_merge import process_email_merge

        result = process_email_merge(str(email.id), force=False)

        assert result == str(email.id)
        mock_service_class.assert_not_called()
        mock_workflow_delay.assert_called_once_with(
            str(email.id),
            force=False,
            language=None,
            scene=None,
        )
        tracer.complete_task.assert_called_once()
        email.refresh_from_db()
        assert email.merged_into_id is None

    @patch("threadline.tasks.email_merge.process_email_workflow.delay")
    @patch("threadline.tasks.email_merge.TaskTracer")
    @patch("threadline.tasks.email_merge.EmailMergeService")
    def test_process_email_merge_marks_email_failed_on_reconcile_error(
        self,
        mock_service_class,
        mock_tracer_class,
        mock_workflow_delay,
    ):
        email = self._create_email(
            message_id="<failing-child@example.com>",
            status="processing",
        )

        mock_service = Mock()
        mock_service.reconcile.side_effect = RuntimeError("merge exploded")
        mock_service_class.return_value = mock_service

        tracer = Mock()
        tracer.context_summary.return_value = "EMAIL_MERGE"
        mock_tracer_class.return_value = tracer

        from threadline.tasks.email_merge import process_email_merge

        with self.assertRaises(RuntimeError):
            process_email_merge(str(email.id), force=True)

        email.refresh_from_db()

        assert email.status == "failed"
        assert "merge exploded" in email.error_message
        mock_workflow_delay.assert_not_called()
        tracer.fail_task.assert_called_once()

    @patch("threadline.tasks.email_merge.process_email_workflow.delay")
    @patch("threadline.tasks.email_merge.TaskTracer")
    @patch("threadline.tasks.email_merge.EmailMergeService")
    def test_process_email_merge_marks_original_failed_when_enqueue_fails(
        self,
        mock_service_class,
        mock_tracer_class,
        mock_workflow_delay,
    ):
        email = self._create_email(
            message_id="<enqueue-child@example.com>",
            status="processing",
        )
        canonical = self._create_email(
            message_id="<enqueue-canonical@example.com>",
            subject="Canonical enqueue target",
            status="processing",
        )

        mock_service = Mock()
        mock_service.reconcile.return_value = (
            canonical,
            Mock(
                should_merge=True,
                reason=EmailMessage.MergeReason.TEXT_SIMILARITY.value,
                sources=(email,),
            ),
        )
        mock_service_class.return_value = mock_service

        tracer = Mock()
        tracer.context_summary.return_value = "EMAIL_MERGE"
        mock_tracer_class.return_value = tracer

        mock_workflow_delay.side_effect = RuntimeError("broker down")

        from threadline.tasks.email_merge import process_email_merge

        with self.assertRaises(RuntimeError):
            process_email_merge(str(email.id), force=True)

        email.refresh_from_db()

        assert email.status == "failed"
        assert "broker down" in email.error_message
        tracer.fail_task.assert_called()

    @patch("threadline.tasks.email_workflow.process_email_workflow.delay")
    def test_workflow_keeps_current_email(self, mock_workflow_delay):
        email = self._create_email(message_id="<child2@example.com>")
        from threadline.tasks.email_workflow import process_email_workflow

        result = process_email_workflow(str(email.id), force=False)

        assert result == str(email.id)
        mock_workflow_delay.assert_not_called()
