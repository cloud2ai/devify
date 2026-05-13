"""
Unit tests for task cleanup functionality

Tests task cleanup utilities and cleanup tasks.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

from threadline.models import EmailTask
from threadline.utils.task_cleanup import (
    cleanup_stale_tasks,
    startup_cleanup,
    cleanup_old_tasks
)


class TaskCleanupTest(TestCase):
    """Test task cleanup functionality"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_cleanup_stale_tasks_success(self):
        """Test successful cleanup of stale tasks"""
        # Create stale running task
        stale_task = EmailTask.objects.create(
            task_type=EmailTask.TaskType.IMAP_FETCH,
            status=EmailTask.TaskStatus.RUNNING,
            started_at=timezone.now() - timedelta(minutes=15)
        )

        # Create fresh running task
        fresh_task = EmailTask.objects.create(
            task_type=EmailTask.TaskType.IMAP_FETCH,
            status=EmailTask.TaskStatus.RUNNING,
            started_at=timezone.now() - timedelta(minutes=5)
        )

        # Execute cleanup
        result = cleanup_stale_tasks()

        # Verify results
        self.assertIn('stale_tasks_cancelled', result)
        self.assertEqual(result['stale_tasks_cancelled'], 1)

        # Verify stale task was cancelled
        stale_task.refresh_from_db()
        self.assertEqual(stale_task.status, EmailTask.TaskStatus.CANCELLED)

        # Verify fresh task was not cancelled
        fresh_task.refresh_from_db()
        self.assertEqual(fresh_task.status, EmailTask.TaskStatus.RUNNING)

    def test_cleanup_stale_tasks_no_stale_tasks(self):
        """Test cleanup when no stale tasks exist"""
        # Create fresh running task
        fresh_task = EmailTask.objects.create(
            task_type=EmailTask.TaskType.IMAP_FETCH,
            status=EmailTask.TaskStatus.RUNNING,
            started_at=timezone.now() - timedelta(minutes=5)
        )

        # Execute cleanup
        result = cleanup_stale_tasks()

        # Verify results
        self.assertEqual(result['stale_tasks_cancelled'], 0)

        # Verify fresh task was not cancelled
        fresh_task.refresh_from_db()
        self.assertEqual(fresh_task.status, EmailTask.TaskStatus.RUNNING)

    def test_cleanup_stale_tasks_exception(self):
        """Test cleanup with exception handling"""
        with patch('threadline.utils.task_cleanup.EmailTask.objects.filter') as mock_filter:
            mock_filter.side_effect = Exception("Database error")

            # Execute cleanup
            result = cleanup_stale_tasks()

            # Verify error handling
            self.assertIn('error', result)

    def test_startup_cleanup_success(self):
        """Test successful startup cleanup"""
        # Create stale tasks
        EmailTask.objects.create(
            task_type=EmailTask.TaskType.IMAP_FETCH,
            status=EmailTask.TaskStatus.RUNNING,
            started_at=timezone.now() - timedelta(minutes=15)
        )

        EmailTask.objects.create(
            task_type=EmailTask.TaskType.HARAKA_FETCH,
            status=EmailTask.TaskStatus.RUNNING,
            started_at=timezone.now() - timedelta(minutes=20)
        )

        with patch('threadline.utils.task_cleanup.force_release_all_locks') as mock_release:
            # Execute startup cleanup
            result = startup_cleanup()

            # Verify results
            self.assertIn('stale_tasks_cancelled', result)
            self.assertIn('running_tasks_cancelled', result)
            mock_release.assert_called_once()

    def test_startup_cleanup_no_stale_tasks(self):
        """Test startup cleanup with no stale tasks"""
        with patch('threadline.utils.task_cleanup.force_release_all_locks') as mock_release:
            # Execute startup cleanup
            result = startup_cleanup()

            # Verify results
            self.assertIn('stale_tasks_cancelled', result)
            self.assertEqual(result['stale_tasks_cancelled'], 0)
            mock_release.assert_called_once()

    def test_startup_cleanup_exception(self):
        """Test startup cleanup with exception handling"""
        with patch('threadline.utils.task_cleanup.EmailTask.objects.filter') as mock_filter:
            mock_filter.side_effect = Exception("Database error")

            # Execute startup cleanup
            result = startup_cleanup()

            # Verify error handling
            self.assertIn('error', result)

    def test_cleanup_old_tasks_deletes_old_completed_tasks(self):
        """Test that old completed tasks are deleted"""
        # Create old completed task
        old_task = EmailTask.objects.create(
            task_type=EmailTask.TaskType.IMAP_FETCH,
            status=EmailTask.TaskStatus.COMPLETED,
            completed_at=timezone.now() - timedelta(days=2)
        )
        old_task_id = old_task.id

        # Create recent completed task
        recent_task = EmailTask.objects.create(
            task_type=EmailTask.TaskType.IMAP_FETCH,
            status=EmailTask.TaskStatus.COMPLETED,
            completed_at=timezone.now() - timedelta(hours=12)
        )
        recent_task_id = recent_task.id

        # Execute cleanup
        result = cleanup_old_tasks(days_old=1)

        # Verify results - at least our old task was deleted
        self.assertIn('old_tasks_deleted', result)
        self.assertGreaterEqual(result['old_tasks_deleted'], 1)

        # Verify old completed task was deleted
        self.assertFalse(EmailTask.objects.filter(id=old_task_id).exists())

        # Verify recent completed task was not deleted
        self.assertTrue(EmailTask.objects.filter(id=recent_task_id).exists())

    def test_cleanup_old_tasks_no_old_tasks(self):
        """Test cleanup when no old tasks exist"""
        # Create recent completed task
        recent_task = EmailTask.objects.create(
            task_type=EmailTask.TaskType.IMAP_FETCH,
            status=EmailTask.TaskStatus.COMPLETED,
            completed_at=timezone.now() - timedelta(hours=12)
        )
        recent_task_id = recent_task.id

        # Execute cleanup
        result = cleanup_old_tasks(days_old=1)

        # Verify results
        self.assertGreaterEqual(result['old_tasks_deleted'], 0)

        # Verify recent task was not deleted
        self.assertTrue(EmailTask.objects.filter(id=recent_task_id).exists())

    def test_cleanup_old_tasks_exception(self):
        """Test cleanup with exception handling"""
        with patch('threadline.utils.task_cleanup.EmailTask.objects.filter') as mock_filter:
            mock_filter.side_effect = Exception("Database error")

            # Execute cleanup
            result = cleanup_old_tasks(days_old=1)

            # Verify error handling
            self.assertIn('error', result)

    def test_cleanup_old_tasks_different_statuses(self):
        """Test cleanup with different task statuses"""
        # Create tasks with different statuses
        completed_task = EmailTask.objects.create(
            task_type=EmailTask.TaskType.IMAP_FETCH,
            status=EmailTask.TaskStatus.COMPLETED,
            completed_at=timezone.now() - timedelta(days=2)
        )
        completed_task_id = completed_task.id

        running_task = EmailTask.objects.create(
            task_type=EmailTask.TaskType.IMAP_FETCH,
            status=EmailTask.TaskStatus.RUNNING,
            started_at=timezone.now() - timedelta(days=2)
        )
        running_task_id = running_task.id

        # Execute cleanup
        result = cleanup_old_tasks(days_old=1)

        # Verify results
        self.assertIn('old_tasks_deleted', result)

        # Verify completed task was deleted
        self.assertFalse(EmailTask.objects.filter(id=completed_task_id).exists())
        # Verify running task was not deleted
        self.assertTrue(EmailTask.objects.filter(id=running_task_id).exists())

    def test_cleanup_old_tasks_without_completed_at(self):
        """Test cleanup of tasks without completed_at"""
        # Create task without completed_at
        task = EmailTask.objects.create(
            task_type=EmailTask.TaskType.IMAP_FETCH,
            status=EmailTask.TaskStatus.COMPLETED
        )
        task_id = task.id

        # Execute cleanup
        result = cleanup_old_tasks(days_old=1)

        # Verify task was not deleted (no completed_at)
        self.assertGreaterEqual(result['old_tasks_deleted'], 0)
        self.assertTrue(EmailTask.objects.filter(id=task_id).exists())

    def test_cleanup_stale_tasks_pending_status(self):
        """Test cleanup of stale pending tasks - uses RUNNING since PENDING doesn't exist"""
        # Create stale pending task (using RUNNING as PENDING doesn't exist)
        pending_task = EmailTask.objects.create(
            task_type=EmailTask.TaskType.IMAP_FETCH,
            status=EmailTask.TaskStatus.RUNNING,
            started_at=timezone.now() - timedelta(minutes=15)
        )

        # Execute cleanup
        result = cleanup_stale_tasks()

        # Verify results
        self.assertEqual(result['stale_tasks_cancelled'], 1)

        # Verify pending task was cancelled
        pending_task.refresh_from_db()
        self.assertEqual(pending_task.status, EmailTask.TaskStatus.CANCELLED)

    def test_cleanup_stale_tasks_without_started_at(self):
        """Test cleanup of tasks without started_at"""
        # Create task without started_at - should not be cancelled
        task = EmailTask.objects.create(
            task_type=EmailTask.TaskType.IMAP_FETCH,
            status=EmailTask.TaskStatus.RUNNING
        )

        # Execute cleanup
        result = cleanup_stale_tasks()

        # Verify task was not cancelled (no started_at)
        self.assertEqual(result['stale_tasks_cancelled'], 0)
        task.refresh_from_db()
        self.assertEqual(task.status, EmailTask.TaskStatus.RUNNING)
