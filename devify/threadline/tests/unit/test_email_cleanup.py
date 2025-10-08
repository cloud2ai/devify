"""
Unit tests for email cleanup functionality

Tests EmailCleanupManager and EmailTaskCleanupManager classes.
Following the pattern of mocking unrelated parts and focusing on
input/output results.
"""

import os
import tempfile
from datetime import timedelta
from unittest.mock import Mock, patch, MagicMock, call

import pytest
from django.test import TestCase, override_settings
from django.utils import timezone

from threadline.models import EmailTask
from threadline.tasks.cleanup import (
    EmailCleanupManager,
    EmailTaskCleanupManager
)


class EmailCleanupManagerTest(TestCase):
    """Test EmailCleanupManager functionality"""

    def setUp(self):
        """Set up test data"""
        self.temp_dir = tempfile.mkdtemp()
        self.inbox_dir = os.path.join(self.temp_dir, 'inbox')
        self.processed_dir = os.path.join(self.temp_dir, 'processed')
        self.failed_dir = os.path.join(self.temp_dir, 'failed')

        os.makedirs(self.inbox_dir)
        os.makedirs(self.processed_dir)
        os.makedirs(self.failed_dir)

    def tearDown(self):
        """Clean up test directories"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @patch('threadline.tasks.cleanup.settings')
    @patch('threadline.tasks.cleanup.TaskTracer')
    def test_cleanup_haraka_files_success(self, mock_tracer, mock_settings):
        """Test successful Haraka files cleanup"""
        mock_settings.EMAIL_CLEANUP_CONFIG = {
            'inbox_timeout_hours': 1,
            'processed_timeout_minutes': 10,
            'failed_timeout_minutes': 10
        }
        mock_settings.HARAKA_EMAIL_BASE_DIR = self.temp_dir

        mock_tracer_instance = MagicMock()
        mock_tracer.return_value = mock_tracer_instance

        self._create_test_email_files(
            self.inbox_dir,
            'test1',
            age_minutes=70
        )
        self._create_test_email_files(
            self.processed_dir,
            'test2',
            age_minutes=15
        )

        manager = EmailCleanupManager()
        result = manager.cleanup_haraka_files()

        self.assertEqual(result['inbox_cleaned'], 1)
        self.assertEqual(result['processed_cleaned'], 1)
        self.assertEqual(result['total_files_removed'], 2)
        self.assertGreater(result['total_size_freed'], 0)

        mock_tracer_instance.create_task.assert_called_once()
        mock_tracer_instance.complete_task.assert_called_once()

    @patch('threadline.tasks.cleanup.settings')
    def test_cleanup_haraka_files_no_files(self, mock_settings):
        """Test cleanup when no files exist"""
        mock_settings.EMAIL_CLEANUP_CONFIG = {
            'inbox_timeout_hours': 1,
            'processed_timeout_minutes': 10,
            'failed_timeout_minutes': 10
        }
        mock_settings.HARAKA_EMAIL_BASE_DIR = self.temp_dir

        with patch('threadline.tasks.cleanup.TaskTracer'):
            manager = EmailCleanupManager()
            result = manager.cleanup_haraka_files()

        self.assertEqual(result['inbox_cleaned'], 0)
        self.assertEqual(result['processed_cleaned'], 0)
        self.assertEqual(result['failed_cleaned'], 0)
        self.assertEqual(result['total_files_removed'], 0)

    @patch('threadline.tasks.cleanup.settings')
    def test_cleanup_haraka_files_partial_cleanup(self, mock_settings):
        """Test cleanup with some files too new to clean"""
        mock_settings.EMAIL_CLEANUP_CONFIG = {
            'inbox_timeout_hours': 1,
            'processed_timeout_minutes': 10,
            'failed_timeout_minutes': 10
        }
        mock_settings.HARAKA_EMAIL_BASE_DIR = self.temp_dir

        self._create_test_email_files(
            self.inbox_dir,
            'old',
            age_minutes=70
        )
        self._create_test_email_files(
            self.inbox_dir,
            'new',
            age_minutes=5
        )

        with patch('threadline.tasks.cleanup.TaskTracer'):
            manager = EmailCleanupManager()
            result = manager.cleanup_haraka_files()

        self.assertEqual(result['inbox_cleaned'], 1)
        self.assertTrue(
            os.path.exists(os.path.join(self.inbox_dir, 'new.eml'))
        )
        self.assertFalse(
            os.path.exists(os.path.join(self.inbox_dir, 'old.eml'))
        )

    @patch('threadline.tasks.cleanup.settings')
    def test_get_directory_stats(self, mock_settings):
        """Test getting directory statistics"""
        mock_settings.HARAKA_EMAIL_BASE_DIR = self.temp_dir

        self._create_test_email_files(self.inbox_dir, 'test1')
        self._create_test_email_files(self.inbox_dir, 'test2')

        manager = EmailCleanupManager()
        stats = manager.get_directory_stats(self.inbox_dir)

        self.assertEqual(stats['file_count'], 2)
        self.assertEqual(stats['meta_files'], 2)
        self.assertEqual(stats['eml_files'], 2)
        self.assertEqual(stats['orphaned_files'], 0)
        self.assertGreater(stats['total_size'], 0)

    @patch('threadline.tasks.cleanup.settings')
    def test_get_directory_stats_with_orphaned_files(self, mock_settings):
        """Test stats with orphaned files"""
        mock_settings.HARAKA_EMAIL_BASE_DIR = self.temp_dir

        self._create_test_email_files(self.inbox_dir, 'complete')

        orphan_eml = os.path.join(self.inbox_dir, 'orphan.eml')
        with open(orphan_eml, 'w') as f:
            f.write('orphaned eml content')

        orphan_meta = os.path.join(self.inbox_dir, 'orphan2.meta')
        with open(orphan_meta, 'w') as f:
            f.write('{}')

        manager = EmailCleanupManager()
        stats = manager.get_directory_stats(self.inbox_dir)

        self.assertEqual(stats['file_count'], 1)
        self.assertEqual(stats['orphaned_files'], 2)

    @patch('threadline.tasks.cleanup.settings')
    def test_get_cleanup_stats(self, mock_settings):
        """Test getting comprehensive cleanup statistics"""
        mock_settings.HARAKA_EMAIL_BASE_DIR = self.temp_dir

        self._create_test_email_files(self.inbox_dir, 'inbox1')
        self._create_test_email_files(self.processed_dir, 'proc1')
        self._create_test_email_files(self.processed_dir, 'proc2')
        self._create_test_email_files(self.failed_dir, 'fail1')

        manager = EmailCleanupManager()
        stats = manager.get_cleanup_stats()

        self.assertEqual(stats['inbox']['file_count'], 1)
        self.assertEqual(stats['processed']['file_count'], 2)
        self.assertEqual(stats['failed']['file_count'], 1)
        self.assertEqual(stats['total_files'], 4)
        self.assertGreater(stats['total_size'], 0)

    @patch('threadline.tasks.cleanup.settings')
    @patch('threadline.tasks.cleanup.TaskTracer')
    @patch('threadline.tasks.cleanup.os.path.join')
    def test_cleanup_haraka_files_with_error(
        self,
        mock_join,
        mock_tracer,
        mock_settings
    ):
        """Test cleanup with errors"""
        mock_settings.EMAIL_CLEANUP_CONFIG = {
            'inbox_timeout_hours': 1,
            'processed_timeout_minutes': 10,
            'failed_timeout_minutes': 10
        }
        mock_settings.HARAKA_EMAIL_BASE_DIR = self.temp_dir

        # Make os.path.join raise an exception
        mock_join.side_effect = Exception('Simulated error')

        mock_tracer_instance = MagicMock()
        mock_tracer.return_value = mock_tracer_instance

        manager = EmailCleanupManager()
        result = manager.cleanup_haraka_files()

        self.assertEqual(result['errors'], 1)
        mock_tracer_instance.fail_task.assert_called_once()

    def _create_test_email_files(
        self,
        directory,
        uuid,
        age_minutes=0
    ):
        """
        Helper to create test email files

        Args:
            directory: Target directory
            uuid: Email UUID
            age_minutes: File age in minutes
        """
        eml_file = os.path.join(directory, f'{uuid}.eml')
        meta_file = os.path.join(directory, f'{uuid}.meta')

        with open(eml_file, 'w') as f:
            f.write('test email content')

        with open(meta_file, 'w') as f:
            f.write('{"to": "test@example.com"}')

        if age_minutes > 0:
            past_time = (
                timezone.now() - timedelta(minutes=age_minutes)
            ).timestamp()
            os.utime(eml_file, (past_time, past_time))
            os.utime(meta_file, (past_time, past_time))


@pytest.mark.django_db(transaction=True, reset_sequences=True)
class EmailTaskCleanupManagerTest(TestCase):
    """Test EmailTaskCleanupManager functionality"""

    def setUp(self):
        """Set up test data"""
        # Clean up any existing EmailTask records from previous tests
        EmailTask.objects.all().delete()

    @patch('threadline.tasks.cleanup.settings')
    @patch('threadline.tasks.cleanup.TaskTracer')
    def test_cleanup_email_tasks_success(self, mock_tracer, mock_settings):
        """Test successful EmailTask cleanup"""
        mock_settings.EMAIL_CLEANUP_CONFIG = {
            'email_task_retention_days': 3
        }

        mock_tracer_instance = MagicMock()
        mock_tracer.return_value = mock_tracer_instance

        old_task = EmailTask.objects.create(
            task_type='IMAP_EMAIL_FETCH',
            status=EmailTask.TaskStatus.COMPLETED,
            completed_at=timezone.now() - timedelta(days=5)
        )
        EmailTask.objects.filter(id=old_task.id).update(
            created_at=timezone.now() - timedelta(days=5)
        )

        recent_task = EmailTask.objects.create(
            task_type='IMAP_EMAIL_FETCH',
            status=EmailTask.TaskStatus.COMPLETED,
            completed_at=timezone.now() - timedelta(days=1)
        )
        EmailTask.objects.filter(id=recent_task.id).update(
            created_at=timezone.now() - timedelta(days=1)
        )

        manager = EmailTaskCleanupManager()
        result = manager.cleanup_email_tasks()

        self.assertEqual(result['tasks_cleaned'], 1)
        self.assertEqual(result['errors'], 0)

        self.assertFalse(EmailTask.objects.filter(id=old_task.id).exists())
        self.assertTrue(EmailTask.objects.filter(id=recent_task.id).exists())

        mock_tracer_instance.create_task.assert_called_once()
        mock_tracer_instance.complete_task.assert_called_once()

    @patch('threadline.tasks.cleanup.settings')
    def test_cleanup_email_tasks_no_old_tasks(self, mock_settings):
        """Test cleanup when no old tasks exist"""
        mock_settings.EMAIL_CLEANUP_CONFIG = {
            'email_task_retention_days': 3
        }

        EmailTask.objects.create(
            task_type='IMAP_EMAIL_FETCH',
            status=EmailTask.TaskStatus.COMPLETED,
            created_at=timezone.now() - timedelta(days=1),
            completed_at=timezone.now() - timedelta(days=1)
        )

        with patch('threadline.tasks.cleanup.TaskTracer'):
            manager = EmailTaskCleanupManager()
            result = manager.cleanup_email_tasks()

        self.assertEqual(result['tasks_cleaned'], 0)
        self.assertEqual(result['errors'], 0)

    @patch('threadline.tasks.cleanup.settings')
    def test_cleanup_email_tasks_batch_deletion(self, mock_settings):
        """Test batch deletion of multiple old tasks"""
        mock_settings.EMAIL_CLEANUP_CONFIG = {
            'email_task_retention_days': 3
        }

        old_date = timezone.now() - timedelta(days=5)
        for i in range(10):
            task = EmailTask.objects.create(
                task_type='IMAP_EMAIL_FETCH',
                status=EmailTask.TaskStatus.COMPLETED,
                completed_at=old_date
            )
            EmailTask.objects.filter(id=task.id).update(created_at=old_date)

        with patch('threadline.tasks.cleanup.TaskTracer'):
            manager = EmailTaskCleanupManager()
            result = manager.cleanup_email_tasks()

        self.assertEqual(result['tasks_cleaned'], 10)
        self.assertEqual(EmailTask.objects.count(), 0)

    @patch('threadline.tasks.cleanup.settings')
    @patch('threadline.tasks.cleanup.TaskTracer')
    @patch('threadline.tasks.cleanup.logger')
    def test_cleanup_email_tasks_with_error(
        self,
        mock_logger,
        mock_tracer,
        mock_settings
    ):
        """Test cleanup with database error"""
        mock_settings.EMAIL_CLEANUP_CONFIG = {
            'email_task_retention_days': 3
        }

        mock_tracer_instance = MagicMock()
        mock_tracer.return_value = mock_tracer_instance

        with patch(
            'threadline.tasks.cleanup.EmailTask.objects.filter',
            side_effect=Exception('Database error')
        ):
            manager = EmailTaskCleanupManager()
            result = manager.cleanup_email_tasks()

        self.assertEqual(result['errors'], 1)
        mock_tracer_instance.fail_task.assert_called_once()

    @patch('threadline.tasks.cleanup.settings')
    def test_cleanup_email_tasks_different_retention(self, mock_settings):
        """Test cleanup with different retention periods"""
        mock_settings.EMAIL_CLEANUP_CONFIG = {
            'email_task_retention_days': 7
        }

        task1 = EmailTask.objects.create(
            task_type='IMAP_EMAIL_FETCH',
            status=EmailTask.TaskStatus.COMPLETED,
            completed_at=timezone.now() - timedelta(days=5)
        )
        EmailTask.objects.filter(id=task1.id).update(
            created_at=timezone.now() - timedelta(days=5)
        )

        task2 = EmailTask.objects.create(
            task_type='IMAP_EMAIL_FETCH',
            status=EmailTask.TaskStatus.COMPLETED,
            completed_at=timezone.now() - timedelta(days=10)
        )
        EmailTask.objects.filter(id=task2.id).update(
            created_at=timezone.now() - timedelta(days=10)
        )

        with patch('threadline.tasks.cleanup.TaskTracer'):
            manager = EmailTaskCleanupManager()
            result = manager.cleanup_email_tasks()

        self.assertEqual(result['tasks_cleaned'], 1)
        self.assertEqual(EmailTask.objects.count(), 1)
