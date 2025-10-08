"""
Unit tests for EmailTask model

Tests EmailTask model fields, state machine, and utility methods.
"""

from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from threadline.models import EmailTask


class EmailTaskModelTest(TestCase):
    """Test EmailTask model functionality"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_email_task_creation(self):
        """Test EmailTask creation with all fields"""
        task = EmailTask.objects.create(
            task_type='IMAP_EMAIL_FETCH',
            status=EmailTask.TaskStatus.PENDING,
            details={'test': 'data'}
        )

        self.assertEqual(task.task_type, 'IMAP_EMAIL_FETCH')
        self.assertEqual(task.status, EmailTask.TaskStatus.PENDING)
        self.assertEqual(task.details, {'test': 'data'})

    def test_email_task_creation_global(self):
        """Test EmailTask creation as global task"""
        task = EmailTask.objects.create(
            task_type='HARAKA_EMAIL_FETCH',
            status=EmailTask.TaskStatus.PENDING
        )

        self.assertEqual(task.task_type, 'HARAKA_EMAIL_FETCH')
        self.assertEqual(task.status, EmailTask.TaskStatus.PENDING)

    def test_task_status_choices(self):
        """Test all task status choices are available"""
        statuses = [
            EmailTask.TaskStatus.PENDING,
            EmailTask.TaskStatus.RUNNING,
            EmailTask.TaskStatus.COMPLETED,
            EmailTask.TaskStatus.FAILED,
            EmailTask.TaskStatus.CANCELLED,
            EmailTask.TaskStatus.SKIPPED,
        ]

        for status in statuses:
            task = EmailTask.objects.create(
                task_type='IMAP_EMAIL_FETCH',
                status=status
            )
            self.assertEqual(task.status, status)

    def test_str_representation(self):
        """Test string representation"""
        task = EmailTask.objects.create(
            task_type='IMAP_EMAIL_FETCH',
            status=EmailTask.TaskStatus.PENDING
        )

        expected = f"EmailTask({task.id}): IMAP_EMAIL_FETCH-pending"
        self.assertEqual(str(task), expected)

    def test_meta_indexes(self):
        """Test model meta indexes"""
        meta = EmailTask._meta
        index_fields = [index.fields for index in meta.indexes]

        self.assertIn(['task_type'], index_fields)
        self.assertIn(['status'], index_fields)
        # Note: started_at index is not in the current model definition

    def test_default_values(self):
        """Test default field values"""
        task = EmailTask.objects.create(
            task_type='IMAP_EMAIL_FETCH'
        )

        self.assertEqual(task.status, EmailTask.TaskStatus.PENDING)
        self.assertEqual(task.details, [])
        self.assertEqual(task.error_message, '')

    def test_task_without_user(self):
        """Test task creation without user (global task)"""
        task = EmailTask.objects.create(
            task_type='HARAKA_EMAIL_FETCH',
            status=EmailTask.TaskStatus.PENDING
        )

        self.assertEqual(task.task_type, 'HARAKA_EMAIL_FETCH')






    def test_task_type_choices(self):
        """Test email source choices"""
        # Test IMAP source
        task = EmailTask.objects.create(
            task_type='IMAP_EMAIL_FETCH'
        )
        self.assertEqual(task.task_type, 'IMAP_EMAIL_FETCH')

        # Test Haraka source
        task = EmailTask.objects.create(
            task_type='HARAKA_EMAIL_FETCH'
        )
        self.assertEqual(task.task_type, 'HARAKA_EMAIL_FETCH')

    def test_task_id_field(self):
        """Test task_id field functionality"""
        task = EmailTask.objects.create(
            task_type='IMAP_EMAIL_FETCH',
            task_id='test-task-123'
        )

        self.assertEqual(task.task_id, 'test-task-123')

    def test_global_task_string_representation(self):
        """Test string representation for global tasks"""
        task = EmailTask.objects.create(
            task_type='HARAKA_EMAIL_FETCH',
            status=EmailTask.TaskStatus.PENDING
        )

        expected = f"EmailTask({task.id}): HARAKA_EMAIL_FETCH-pending"
        self.assertEqual(str(task), expected)
