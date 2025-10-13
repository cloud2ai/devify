"""
Unit tests for email fetch tasks

Tests email fetch task functionality including scheduling, IMAP, and Haraka tasks.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone

from threadline.models import EmailTask, Settings
from threadline.tasks.email_fetch import (
    imap_email_fetch,
    haraka_email_fetch,
    fetch_user_imap_emails,
    cleanup_old_tasks
)
from threadline.tasks.scheduler import schedule_email_fetch
from threadline.utils.task_cleanup import startup_cleanup


class EmailFetchTasksTest(TestCase):
    """Test email fetch tasks functionality"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Create email config for user
        Settings.objects.create(
            user=self.user,
            key='email_config',
            value={
                'imap_config': {
                    'host': 'imap.example.com',
                    'port': 993,
                    'username': 'test@example.com',
                    'password': 'password123'
                },
                'filter_config': {
                    'folder': 'INBOX',
                    'filters': [],
                    'max_age_days': 7
                }
            },
            is_active=True
        )

    @patch('threadline.tasks.email_fetch.acquire_task_lock')
    @patch('threadline.tasks.email_fetch.cleanup_stale_tasks')
    @patch('threadline.tasks.email_fetch.imap_email_fetch.delay')
    @patch('threadline.tasks.email_fetch.haraka_email_fetch.delay')
    @patch('threadline.tasks.email_fetch.release_task_lock')
    def test_schedule_email_fetch_success(self, mock_release, mock_haraka_delay,
                                        mock_imap_delay, mock_cleanup, mock_acquire):
        """Test successful email fetch scheduling"""
        # Mock successful lock acquisition
        mock_acquire.return_value = True

        # Mock task delays
        mock_imap_result = Mock()
        mock_imap_result.id = 'imap-task-123'
        mock_imap_delay.return_value = mock_imap_result

        mock_haraka_result = Mock()
        mock_haraka_result.id = 'haraka-task-456'
        mock_haraka_delay.return_value = mock_haraka_result

        # Execute task
        result = schedule_email_fetch()

        # Verify results
        self.assertEqual(result['status'], 'scheduled')
        self.assertEqual(result['imap_task_id'], 'imap-task-123')
        self.assertEqual(result['haraka_task_id'], 'haraka-task-456')

        # Verify calls
        mock_acquire.assert_called_once_with('email_fetch', timeout=600)
        mock_cleanup.assert_called_once()
        mock_imap_delay.assert_called_once()
        mock_haraka_delay.assert_called_once()
        mock_release.assert_called_once_with('email_fetch')

    @patch('threadline.tasks.email_fetch.acquire_task_lock')
    def test_schedule_email_fetch_lock_failed(self, mock_acquire):
        """Test email fetch scheduling when lock acquisition fails"""
        # Mock failed lock acquisition
        mock_acquire.return_value = False

        # Execute task
        result = schedule_email_fetch()

        # Verify results
        self.assertEqual(result['status'], 'skipped')
        self.assertEqual(result['reason'], 'task_lock_exists')

    @patch('threadline.tasks.email_fetch.EmailTask.objects.create')
    @patch('threadline.tasks.email_fetch.User.objects.filter')
    @patch('threadline.tasks.email_fetch.EmailConfigManager.get_email_config')
    @patch('threadline.tasks.email_fetch.fetch_user_imap_emails')
    def test_imap_email_fetch_success(self, mock_fetch, mock_get_config,
                                     mock_filter, mock_create):
        """Test successful IMAP email fetch task"""
        # Mock task creation
        mock_task = Mock()
        mock_task.add_execution_log = Mock()
        mock_task.update_status = Mock()
        mock_task.emails_processed = 0
        mock_create.return_value = mock_task

        # Mock user filtering
        mock_filter.return_value = [self.user]

        # Mock email config
        mock_get_config.return_value = {
            'imap_config': {
                'host': 'imap.example.com',
                'port': 993,
                'username': 'test@example.com',
                'password': 'password123'
            }
        }

        # Mock fetch result
        mock_fetch.return_value = {
            'emails_processed': 5,
            'errors': 0,
            'status': 'completed'
        }

        # Execute task
        result = imap_email_fetch()

        # Verify results
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['processed_users'], 1)
        self.assertEqual(result['emails_processed'], 5)
        self.assertEqual(result['errors'], 0)

        # Verify calls
        mock_create.assert_called_once()
        mock_task.update_status.assert_called()
        mock_fetch.assert_called_once_with(self.user.id)

    @patch('threadline.tasks.email_fetch.EmailTask.objects.create')
    @patch('threadline.tasks.email_fetch.User.objects.filter')
    @patch('threadline.tasks.email_fetch.EmailConfigManager.get_email_config')
    def test_imap_email_fetch_no_config(self, mock_get_config, mock_filter,
                                       mock_create):
        """Test IMAP email fetch when user has no config"""
        # Mock task creation
        mock_task = Mock()
        mock_task.add_execution_log = Mock()
        mock_task.update_status = Mock()
        mock_create.return_value = mock_task

        # Mock user filtering
        mock_filter.return_value = [self.user]

        # Mock no email config
        mock_get_config.return_value = {}

        # Execute task
        result = imap_email_fetch()

        # Verify results
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['processed_users'], 0)
        self.assertEqual(result['emails_processed'], 0)
        self.assertEqual(result['errors'], 0)

    @patch('threadline.tasks.email_fetch.EmailTask.objects.create')
    @patch('threadline.tasks.email_fetch.User.objects.filter')
    def test_imap_email_fetch_exception(self, mock_filter, mock_create):
        """Test IMAP email fetch with exception"""
        # Mock task creation
        mock_task = Mock()
        mock_task.add_execution_log = Mock()
        mock_task.update_status = Mock()
        mock_create.return_value = mock_task

        # Mock user filtering to raise exception
        mock_filter.side_effect = Exception("Database error")

        # Execute task and expect exception
        with self.assertRaises(Exception):
            imap_email_fetch()

        # Verify task was marked as failed
        mock_task.update_status.assert_called_with('FAILED')

    @patch('threadline.tasks.email_fetch.EmailSaveService')
    @patch('threadline.tasks.email_fetch.EmailProcessor')
    def test_haraka_email_fetch_success(self, mock_processor_class,
                                       mock_save_service_class):
        """Test successful Haraka email fetch task"""
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
                'subject': 'Test Email',
                'recipients': ['test@example.com'],
                'message_id': 'test-123'
            }
        ]

        # Execute task
        result = haraka_email_fetch()

        # Verify results
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['emails_processed'], 1)
        self.assertEqual(result['errors'], 0)

        # Verify calls
        mock_save_service.find_user_by_recipient.assert_called_once()
        mock_save_service.save_email.assert_called_once()

    @patch('threadline.tasks.email_fetch.EmailSaveService')
    @patch('threadline.tasks.email_fetch.EmailProcessor')
    def test_haraka_email_fetch_no_user_found(self, mock_processor_class,
                                             mock_save_service_class):
        """Test Haraka email fetch when no user found"""
        # Mock save service
        mock_save_service = Mock()
        mock_save_service_class.return_value = mock_save_service
        mock_save_service.find_user_by_recipient.return_value = None

        # Mock processor
        mock_processor = Mock()
        mock_processor_class.return_value = mock_processor
        mock_processor.process_emails.return_value = [
            {
                'subject': 'Test Email',
                'recipients': ['unknown@example.com'],
                'message_id': 'test-123'
            }
        ]

        # Execute task
        result = haraka_email_fetch()

        # Verify results
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['emails_processed'], 0)
        self.assertEqual(result['errors'], 0)

        # Verify no save was attempted
        mock_save_service.save_email.assert_not_called()

    @patch('threadline.tasks.email_fetch.EmailSaveService')
    @patch('threadline.tasks.email_fetch.EmailProcessor')
    def test_haraka_email_fetch_save_error(self, mock_processor_class,
                                          mock_save_service_class):
        """Test Haraka email fetch with save error"""
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
                'subject': 'Test Email',
                'recipients': ['test@example.com'],
                'message_id': 'test-123'
            }
        ]

        # Execute task
        result = haraka_email_fetch()

        # Verify results
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['emails_processed'], 0)
        self.assertEqual(result['errors'], 1)

    @patch('threadline.tasks.email_fetch.EmailConfigManager.get_email_config')
    @patch('threadline.tasks.email_fetch.EmailProcessor')
    @patch('threadline.tasks.email_fetch.EmailSaveService')
    def test_fetch_user_imap_emails_success(self, mock_save_service_class,
                                           mock_processor_class, mock_get_config):
        """Test successful user IMAP email fetch"""
        # Mock email config
        mock_get_config.return_value = {
            'imap_config': {
                'host': 'imap.example.com',
                'port': 993,
                'username': 'test@example.com',
                'password': 'password123'
            }
        }

        # Mock save service
        mock_save_service = Mock()
        mock_save_service_class.return_value = mock_save_service
        mock_save_service.save_email.return_value = Mock(id=123)

        # Mock processor
        mock_processor = Mock()
        mock_processor_class.return_value = mock_processor
        mock_processor.process_emails.return_value = [
            {
                'subject': 'Test Email',
                'message_id': 'test-123'
            }
        ]

        # Execute task
        result = fetch_user_imap_emails(self.user.id)

        # Verify results
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['emails_processed'], 1)
        self.assertEqual(result['errors'], 0)

    @patch('threadline.tasks.email_fetch.EmailConfigManager.get_email_config')
    def test_fetch_user_imap_emails_no_config(self, mock_get_config):
        """Test user IMAP email fetch when no config"""
        # Mock no email config
        mock_get_config.return_value = {}

        # Execute task
        result = fetch_user_imap_emails(self.user.id)

        # Verify results
        self.assertEqual(result['status'], 'skipped')
        self.assertEqual(result['reason'], 'no_imap_config')

    @patch('threadline.tasks.email_fetch.EmailConfigManager.get_email_config')
    def test_fetch_user_imap_emails_exception(self, mock_get_config):
        """Test user IMAP email fetch with exception"""
        # Mock exception
        mock_get_config.side_effect = Exception("Database error")

        # Execute task and expect exception
        with self.assertRaises(Exception):
            fetch_user_imap_emails(self.user.id)

    @patch('threadline.tasks.email_fetch.cleanup_old_tasks')
    def test_cleanup_old_tasks_success(self, mock_cleanup):
        """Test successful cleanup old tasks"""
        mock_cleanup.return_value = {
            'completed_cleaned': 5,
            'failed_cleaned': 2,
            'total_cleaned': 7
        }

        result = cleanup_old_tasks()

        # Verify results
        self.assertEqual(result['completed_cleaned'], 5)
        self.assertEqual(result['failed_cleaned'], 2)
        self.assertEqual(result['total_cleaned'], 7)

    @patch('threadline.tasks.email_fetch.startup_cleanup')
    def test_startup_cleanup_success(self, mock_startup_cleanup):
        """Test successful startup cleanup"""
        mock_startup_cleanup.return_value = {
            'cleaned_tasks': 3,
            'status': 'completed'
        }

        result = startup_cleanup()

        # Verify results
        self.assertEqual(result['cleaned_tasks'], 3)
        self.assertEqual(result['status'], 'completed')
    def test_imap_email_fetch_success(self, mock_fetch, mock_get_config,
                                    mock_users, mock_create):
        """Test successful IMAP email fetch"""
        # Mock task creation
        mock_task = Mock()
        mock_task.id = 'task-123'
        mock_create.return_value = mock_task

        # Mock users
        mock_users.return_value.filter.return_value = [self.user]

        # Mock email config
        mock_get_config.return_value = {
            'imap_config': {'host': 'imap.example.com'},
            'filter_config': {'folder': 'INBOX'}
        }

        # Mock fetch result
        mock_fetch.return_value = {'emails_processed': 5, 'errors': 0}

        # Execute task
        result = imap_email_fetch()

        # Verify results
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['processed_users'], 1)
        self.assertEqual(result['emails_processed'], 5)
        self.assertEqual(result['error_count'], 0)

    @patch('threadline.tasks.email_fetch.EmailTask.objects.create')
    @patch('threadline.tasks.email_fetch.User.objects.filter')
    def test_imap_email_fetch_no_users(self, mock_users, mock_create):
        """Test IMAP email fetch with no active users"""
        # Mock task creation
        mock_task = Mock()
        mock_task.id = 'task-123'
        mock_create.return_value = mock_task

        # Mock no users
        mock_users.return_value.filter.return_value = []

        # Execute task
        result = imap_email_fetch()

        # Verify results
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['processed_users'], 0)
        self.assertEqual(result['emails_processed'], 0)
        self.assertEqual(result['error_count'], 0)

    @patch('threadline.tasks.email_fetch.EmailSaveService')
    @patch('threadline.tasks.email_fetch.EmailProcessor')
    def test_haraka_email_fetch_success(self, mock_processor_class, mock_service_class):
        """Test successful Haraka email fetch"""
        # Mock processor
        mock_processor = Mock()
        mock_processor_class.return_value = mock_processor

        # Mock email data
        mock_email_data = {
            'subject': 'Test Email',
            'recipients': ['test@example.com'],
            'message_id': 'test-123'
        }
        mock_processor.process_emails.return_value = [mock_email_data]

        # Mock save service
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.find_user_by_recipient.return_value = self.user
        mock_service.save_email.return_value = Mock(id='email-123')

        # Execute task
        result = haraka_email_fetch()

        # Verify results
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['emails_processed'], 1)
        self.assertEqual(result['errors'], 0)

    @patch('threadline.tasks.email_fetch.EmailConfigManager.get_email_config')
    @patch('threadline.tasks.email_fetch.EmailProcessor')
    @patch('threadline.tasks.email_fetch.EmailSaveService')
    def test_fetch_user_imap_emails_success(self, mock_service_class,
                                          mock_processor_class, mock_get_config):
        """Test successful user IMAP email fetch"""
        # Mock email config
        mock_get_config.return_value = {
            'imap_config': {'host': 'imap.example.com'},
            'filter_config': {'folder': 'INBOX'}
        }

        # Mock processor
        mock_processor = Mock()
        mock_processor_class.return_value = mock_processor

        # Mock email data
        mock_email_data = {
            'subject': 'Test Email',
            'message_id': 'test-123'
        }
        mock_processor.process_emails.return_value = [mock_email_data]

        # Mock save service
        mock_service = Mock()
        mock_service_class.return_value = mock_service

        # Execute task
        result = fetch_user_imap_emails(self.user.id)

        # Verify results
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['emails_processed'], 1)
        self.assertEqual(result['errors'], 0)

    @patch('threadline.tasks.email_fetch.EmailConfigManager.get_email_config')
    def test_fetch_user_imap_emails_no_config(self, mock_get_config):
        """Test user IMAP email fetch with no config"""
        # Mock no config
        mock_get_config.return_value = None

        # Execute task
        result = fetch_user_imap_emails(self.user.id)

        # Verify results
        self.assertEqual(result['status'], 'skipped')
        self.assertEqual(result['reason'], 'no_imap_config')

    @patch('threadline.tasks.email_fetch.cleanup_old_tasks')
    def test_cleanup_old_tasks_success(self, mock_cleanup):
        """Test cleanup old tasks success"""
        # Mock cleanup result
        mock_cleanup.return_value = {'deleted_count': 5}

        # Execute task
        result = cleanup_old_tasks()

        # Verify results
        self.assertEqual(result['deleted_count'], 5)
        mock_cleanup.assert_called_once_with(days_old=1)

    @patch('threadline.tasks.email_fetch.startup_cleanup')
    def test_startup_cleanup_success(self, mock_startup):
        """Test startup cleanup success"""
        # Mock startup cleanup result
        mock_startup.return_value = {'cleaned_count': 3}

        # Execute task
        result = startup_cleanup()

        # Verify results
        self.assertEqual(result['cleaned_count'], 3)
        mock_startup.assert_called_once()

    def test_task_decorators(self):
        """Test that tasks have proper decorators"""
        # Check that tasks are decorated with @shared_task
        self.assertTrue(hasattr(schedule_email_fetch, 'delay'))
        self.assertTrue(hasattr(imap_email_fetch, 'delay'))
        self.assertTrue(hasattr(haraka_email_fetch, 'delay'))
        self.assertTrue(hasattr(fetch_user_imap_emails, 'delay'))
        self.assertTrue(hasattr(cleanup_old_tasks, 'delay'))
        self.assertTrue(hasattr(startup_cleanup, 'delay'))

    @patch('threadline.tasks.email_fetch.acquire_task_lock')
    @patch('threadline.tasks.email_fetch.cleanup_stale_tasks')
    @patch('threadline.tasks.email_fetch.imap_email_fetch.delay')
    @patch('threadline.tasks.email_fetch.haraka_email_fetch.delay')
    @patch('threadline.tasks.email_fetch.release_task_lock')
    def test_schedule_email_fetch_exception_handling(self, mock_release,
                                                   mock_haraka_delay,
                                                   mock_imap_delay,
                                                   mock_cleanup,
                                                   mock_acquire):
        """Test exception handling in schedule_email_fetch"""
        # Mock successful lock acquisition
        mock_acquire.return_value = True

        # Mock exception in cleanup
        mock_cleanup.side_effect = Exception("Cleanup failed")

        # Execute task and expect exception
        with self.assertRaises(Exception):
            schedule_email_fetch()

        # Verify release was called even on exception
        mock_release.assert_called_once_with('email_fetch')
