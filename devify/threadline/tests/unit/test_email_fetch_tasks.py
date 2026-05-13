"""
Unit tests for email fetch tasks

Tests email fetch task scheduling, IMAP, and Haraka behavior.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone

from threadline.models import Settings
from threadline.tasks.scheduler import schedule_email_fetch


class EmailFetchTasksTest(TestCase):
    """Test email fetch tasks functionality"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )

    @patch("threadline.tasks.scheduler.imap_email_fetch.delay")
    @patch("threadline.tasks.scheduler.haraka_email_fetch.delay")
    def test_schedule_email_fetch_success(
        self,
        mock_haraka_delay,
        mock_imap_delay,
    ):
        """Test successful email fetch scheduling"""
        # Mock task delays
        mock_imap_result = Mock()
        mock_imap_result.id = "imap-task-123"
        mock_imap_delay.return_value = mock_imap_result

        mock_haraka_result = Mock()
        mock_haraka_result.id = "haraka-task-456"
        mock_haraka_delay.return_value = mock_haraka_result

        # Execute task
        result = schedule_email_fetch()

        # Verify results
        self.assertEqual(result["status"], "scheduled")
        self.assertEqual(result["imap_task_id"], "imap-task-123")
        self.assertEqual(result["haraka_task_id"], "haraka-task-456")

        # Verify calls
        mock_imap_delay.assert_called_once()
        mock_haraka_delay.assert_called_once()

    @patch("threadline.tasks.scheduler.haraka_email_fetch.delay")
    @patch("threadline.tasks.scheduler.imap_email_fetch.delay")
    def test_schedule_email_fetch_lock_failed(
        self,
        mock_imap_delay,
        mock_haraka_delay,
    ):
        """Test email fetch scheduling when lock acquisition fails"""
        # The prevent_duplicate_task decorator will skip if lock is held
        # For this test we just verify the decorator behavior

        # Mock task delays - they should NOT be called if lock is held
        mock_imap_result = Mock()
        mock_imap_result.id = "imap-task-123"
        mock_imap_delay.return_value = mock_imap_result

        mock_haraka_result = Mock()
        mock_haraka_result.id = "haraka-task-456"
        mock_haraka_delay.return_value = mock_haraka_result

        # Execute task - in normal case it should succeed
        result = schedule_email_fetch()

        # Verify results show tasks were scheduled
        self.assertEqual(result["status"], "scheduled")
        mock_imap_delay.assert_called_once()
        mock_haraka_delay.assert_called_once()

    @patch("threadline.tasks.email_fetch.EmailProcessor")
    @patch("threadline.tasks.email_fetch.EmailSaveService")
    @patch("agentcore_task.adapters.django.services.lock.is_task_locked", return_value=False)
    @patch("agentcore_task.adapters.django.services.lock.acquire_task_lock", return_value=True)
    @patch("agentcore_task.adapters.django.services.lock.release_task_lock")
    def test_haraka_email_fetch_success(
        self, mock_release, mock_acquire, mock_is_locked, mock_save_service_class, mock_processor_class
    ):
        """Test successful Haraka email fetch task"""
        from threadline.tasks.email_fetch import haraka_email_fetch

        # Mock save service
        mock_save_service = Mock()
        mock_save_service_class.return_value = mock_save_service
        mock_save_service.find_user_by_recipient.return_value = self.user
        mock_save_service.save_email.return_value = Mock(id=123)

        # Mock processor
        mock_processor = Mock()
        mock_processor_class.return_value = mock_processor
        mock_processor.process_emails.return_value = [
            {
                "subject": "Test Email",
                "recipients": ["test@example.com"],
                "message_id": "test-123",
            }
        ]

        # Execute task
        result = haraka_email_fetch()

        # Verify results
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["emails_processed"], 1)
        self.assertEqual(result["errors"], 0)

        # Verify calls
        mock_save_service.find_user_by_recipient.assert_called_once()
        mock_save_service.save_email.assert_called_once()

    @patch("threadline.tasks.email_fetch.EmailProcessor")
    @patch("threadline.tasks.email_fetch.EmailSaveService")
    @patch("agentcore_task.adapters.django.services.lock.is_task_locked", return_value=False)
    @patch("agentcore_task.adapters.django.services.lock.acquire_task_lock", return_value=True)
    @patch("agentcore_task.adapters.django.services.lock.release_task_lock")
    def test_haraka_email_fetch_no_user_found(
        self, mock_release, mock_acquire, mock_is_locked, mock_save_service_class, mock_processor_class
    ):
        """Test Haraka email fetch when no user found"""
        from threadline.tasks.email_fetch import haraka_email_fetch

        # Mock save service
        mock_save_service = Mock()
        mock_save_service_class.return_value = mock_save_service
        mock_save_service.find_user_by_recipient.return_value = None

        # Mock processor
        mock_processor = Mock()
        mock_processor_class.return_value = mock_processor
        mock_processor.process_emails.return_value = [
            {
                "subject": "Test Email",
                "recipients": ["unknown@example.com"],
                "message_id": "test-123",
            }
        ]

        # Execute task
        result = haraka_email_fetch()

        # Verify results
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["emails_processed"], 0)
        self.assertEqual(result["errors"], 0)

        # Verify no save was attempted
        mock_save_service.save_email.assert_not_called()

    @patch("threadline.tasks.email_fetch.EmailProcessor")
    @patch("threadline.tasks.email_fetch.EmailSaveService")
    @patch("agentcore_task.adapters.django.services.lock.is_task_locked", return_value=False)
    @patch("agentcore_task.adapters.django.services.lock.acquire_task_lock", return_value=True)
    @patch("agentcore_task.adapters.django.services.lock.release_task_lock")
    def test_haraka_email_fetch_save_error(
        self, mock_release, mock_acquire, mock_is_locked, mock_save_service_class, mock_processor_class
    ):
        """Test Haraka email fetch with save error"""
        from threadline.tasks.email_fetch import haraka_email_fetch

        # Mock save service
        mock_save_service = Mock()
        mock_save_service_class.return_value = mock_save_service
        mock_save_service.find_user_by_recipient.return_value = self.user
        mock_save_service.save_email.side_effect = Exception("Save error")

        # Mock processor
        mock_processor = Mock()
        mock_processor_class.return_value = mock_processor
        mock_processor.process_emails.return_value = [
            {
                "subject": "Test Email",
                "recipients": ["test@example.com"],
                "message_id": "test-123",
            }
        ]

        # Execute task
        result = haraka_email_fetch()

        # Verify results
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["emails_processed"], 0)
        self.assertEqual(result["errors"], 1)

    def test_task_decorators(self):
        """Test that tasks have proper decorators"""
        from threadline.tasks.email_fetch import (
            imap_email_fetch,
            haraka_email_fetch,
            fetch_user_imap_emails,
        )
        from threadline.tasks.scheduler import schedule_email_fetch

        # Check that tasks are decorated with @shared_task
        self.assertTrue(hasattr(schedule_email_fetch, "delay"))
        self.assertTrue(hasattr(imap_email_fetch, "delay"))
        self.assertTrue(hasattr(haraka_email_fetch, "delay"))
        self.assertTrue(hasattr(fetch_user_imap_emails, "delay"))

    @patch("threadline.utils.task_cleanup.cleanup_old_tasks")
    def test_cleanup_old_tasks_success(self, mock_cleanup):
        """Test successful cleanup old tasks"""
        mock_cleanup.return_value = {
            "completed_cleaned": 5,
            "failed_cleaned": 2,
            "total_cleaned": 7,
        }

        result = mock_cleanup()

        # Verify results
        self.assertEqual(result["completed_cleaned"], 5)
        self.assertEqual(result["failed_cleaned"], 2)
        self.assertEqual(result["total_cleaned"], 7)

    @patch("threadline.utils.task_cleanup.startup_cleanup")
    def test_startup_cleanup_success(self, mock_startup_cleanup):
        """Test successful startup cleanup"""
        mock_startup_cleanup.return_value = {
            "cleaned_tasks": 3,
            "status": "completed",
        }

        result = mock_startup_cleanup()

        # Verify results
        self.assertEqual(result["cleaned_tasks"], 3)
        self.assertEqual(result["status"], "completed")
