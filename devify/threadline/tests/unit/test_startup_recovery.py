"""
Unit tests for Threadline startup recovery.
"""

from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from threadline.models import EmailMessage
from threadline.tests.fixtures.factories import (
    EmailMessageFactory,
    UserFactory,
)


class ThreadlineStartupRecoveryTest(TestCase):
    def setUp(self):
        self.user = UserFactory(username="recovery-test-user")

    @patch("agentcore_task.adapters.django.services.lock.release_task_lock")
    @patch("agentcore_task.adapters.django.services.lock.acquire_task_lock")
    @patch("threadline.services.startup_recovery.process_email_merge.delay")
    def test_requeues_only_stale_processing_emails(
        self,
        mock_delay,
        mock_acquire_lock,
        mock_release_lock,
    ):
        old_email = EmailMessageFactory(
            user=self.user,
            status="processing",
            subject="Old processing email",
        )
        fresh_email = EmailMessageFactory(
            user=self.user,
            status="processing",
            subject="Fresh processing email",
        )
        EmailMessage.objects.filter(pk=old_email.pk).update(
            updated_at=timezone.now() - timedelta(minutes=40)
        )
        EmailMessage.objects.filter(pk=fresh_email.pk).update(
            updated_at=timezone.now() - timedelta(minutes=5)
        )

        mock_acquire_lock.return_value = True

        from threadline.services.startup_recovery import (
            recover_stuck_processing_emails,
        )

        result = recover_stuck_processing_emails(timeout_minutes=30)

        assert result["status"] == "success"
        assert result["candidate_count"] == 1
        assert result["requeued_count"] == 1
        mock_delay.assert_called_once_with(
            str(old_email.id),
            force=False,
            trigger_source="startup_recovery",
        )
        mock_release_lock.assert_called_once()

    @patch("agentcore_task.adapters.django.services.lock.release_task_lock")
    @patch("agentcore_task.adapters.django.services.lock.acquire_task_lock")
    @patch("threadline.services.startup_recovery.process_email_merge.delay")
    def test_skips_when_recovery_lock_is_held(
        self,
        mock_delay,
        mock_acquire_lock,
        mock_release_lock,
    ):
        mock_acquire_lock.return_value = False

        from threadline.services.startup_recovery import (
            recover_stuck_processing_emails,
        )

        result = recover_stuck_processing_emails()

        assert result["status"] == "skipped"
        assert result["requeued_count"] == 0
        mock_delay.assert_not_called()
        mock_release_lock.assert_not_called()
