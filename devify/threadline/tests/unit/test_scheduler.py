"""
Unit tests for stuck email scheduler behavior.
"""

from datetime import timedelta
from unittest.mock import Mock, patch

from django.test import TestCase
from django.utils import timezone

from threadline.models import EmailMessage

from ..fixtures.factories import EmailMessageFactory, UserFactory


class StuckEmailSchedulerTest(TestCase):
    def setUp(self):
        self.user = UserFactory(username="scheduler-test-user")

    @patch("threadline.tasks.scheduler.cleanup_stale_tasks")
    @patch("threadline.tasks.scheduler.TaskTracer")
    @patch("threadline.tasks.scheduler.process_email_merge.delay")
    def test_stuck_cleanup_includes_merged_children(
        self,
        mock_delay,
        mock_tracer_class,
        mock_cleanup,
    ):
        """
        Merged children should still be retried by stuck cleanup.
        """
        tracer = Mock()
        tracer.context_summary.return_value = "STUCK_EMAIL_RESET"
        tracer.create_task.return_value = None
        tracer.append_task.return_value = None
        tracer.complete_task.return_value = None
        tracer.fail_task.return_value = None
        mock_tracer_class.return_value = tracer

        canonical = EmailMessageFactory(
            user=self.user,
            subject="Canonical thread",
            status="fetched",
        )
        child = EmailMessageFactory(
            user=self.user,
            subject="Canonical thread",
            status="fetched",
            merged_into=canonical,
        )

        old_ts = timezone.now() - timedelta(minutes=90)
        EmailMessage.objects.filter(pk__in=[canonical.pk, child.pk]).update(
            updated_at=old_ts
        )

        from threadline.tasks.scheduler import schedule_reset_stuck_emails

        result = schedule_reset_stuck_emails(timeout_minutes=30)

        assert result["stuck_count"] == 2
        assert mock_delay.call_count == 2
        assert {call.args[0] for call in mock_delay.call_args_list} == {
            str(canonical.id),
            str(child.id),
        }
        child.refresh_from_db()
        assert child.fetch_retry_count == 0
        mock_cleanup.assert_called_once()
