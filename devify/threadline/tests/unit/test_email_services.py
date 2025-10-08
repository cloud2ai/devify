"""
Unit tests for email services

Tests EmailConfigManager and EmailSaveService functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone

from threadline.models import Settings, EmailMessage, EmailStatus, EmailAlias
from threadline.utils.email.config import EmailConfigManager, EmailSource
from threadline.utils.email.service import EmailSaveService


class EmailConfigManagerTest(TestCase):
    """Test EmailConfigManager functionality"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_detect_email_source_imap(self):
        """Test detecting IMAP email source"""
        # Create IMAP config
        Settings.objects.create(
            user=self.user,
            key='email_config',
            value={
                'imap_config': {
                    'host': 'imap.example.com',
                    'port': 993,
                    'username': 'test@example.com',
                    'password': 'password123'
                }
            },
            is_active=True
        )

        source = EmailConfigManager.detect_email_source(self.user.id)
        self.assertEqual(source, EmailSource.IMAP)

    def test_detect_email_source_file(self):
        """Test detecting FILE email source"""
        # Create file config
        Settings.objects.create(
            user=self.user,
            key='email_config',
            value={
                'file_config': {
                    'email_directory': '/path/to/emails'
                }
            },
            is_active=True
        )

        source = EmailConfigManager.detect_email_source(self.user.id)
        self.assertEqual(source, EmailSource.FILE)

    def test_detect_email_source_auto_assign(self):
        """Test detecting FILE email source with auto_assign mode"""
        # Create auto_assign config
        Settings.objects.create(
            user=self.user,
            key='email_config',
            value={
                'mode': 'auto_assign'
            },
            is_active=True
        )

        source = EmailConfigManager.detect_email_source(self.user.id)
        self.assertEqual(source, EmailSource.FILE)

    def test_detect_email_source_default(self):
        """Test default email source when no config"""
        source = EmailConfigManager.detect_email_source(self.user.id)
        self.assertEqual(source, EmailSource.IMAP)

    def test_detect_email_source_exception(self):
        """Test email source detection with exception"""
        with patch('threadline.utils.email.config.Settings.objects.get') as mock_get:
            mock_get.side_effect = Exception("Database error")

            source = EmailConfigManager.detect_email_source(self.user.id)
            self.assertEqual(source, EmailSource.IMAP)

    def test_get_email_config_success(self):
        """Test successful email config retrieval"""
        config_data = {
            'imap_config': {
                'host': 'imap.example.com',
                'port': 993,
                'username': 'test@example.com',
                'password': 'password123'
            }
        }

        Settings.objects.create(
            user=self.user,
            key='email_config',
            value=config_data,
            is_active=True
        )

        config = EmailConfigManager.get_email_config(self.user.id)
        self.assertEqual(config, config_data)

    def test_get_email_config_not_found(self):
        """Test email config retrieval when not found"""
        config = EmailConfigManager.get_email_config(self.user.id)
        self.assertEqual(config, {})

    def test_get_email_config_exception(self):
        """Test email config retrieval with exception"""
        with patch('threadline.utils.email.config.Settings.objects.get') as mock_get:
            mock_get.side_effect = Exception("Database error")

            config = EmailConfigManager.get_email_config(self.user.id)
            self.assertEqual(config, {})

    def test_update_fetch_time_success(self):
        """Test successful fetch time update"""
        # Create initial config
        Settings.objects.create(
            user=self.user,
            key='email_config',
            value={
                'filter_config': {
                    'last_email_fetch_time': '2023-01-01T00:00:00Z'
                }
            },
            is_active=True
        )

        new_time = timezone.now()
        EmailConfigManager.update_fetch_time(self.user.id, new_time)

        # Verify update
        setting = Settings.objects.get(user=self.user, key='email_config')
        expected_time = new_time.isoformat()
        self.assertEqual(
            setting.value['filter_config']['last_email_fetch_time'],
            expected_time
        )

    def test_update_fetch_time_no_config(self):
        """Test fetch time update when no config exists"""
        new_time = timezone.now()
        # Should not raise exception
        EmailConfigManager.update_fetch_time(self.user.id, new_time)

    def test_update_fetch_time_exception(self):
        """Test fetch time update with exception"""
        with patch('threadline.utils.email.config.Settings.objects.get') as mock_get:
            mock_get.side_effect = Exception("Database error")

            new_time = timezone.now()
            # Should not raise exception
            EmailConfigManager.update_fetch_time(self.user.id, new_time)


class EmailSaveServiceTest(TestCase):
    """Test EmailSaveService functionality"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.service = EmailSaveService()

    def test_save_email_success(self):
        """Test successful email saving"""
        email_data = {
            'subject': 'Test Email',
            'sender': 'sender@example.com',
            'recipients': ['test@example.com'],
            'received_at': timezone.now(),
            'raw_content': 'Raw email content',
            'html_content': '<p>HTML content</p>',
            'text_content': 'Text content',
            'message_id': 'test-message-123',
            'attachments': []
        }

        email_msg = self.service.save_email(self.user.id, email_data)

        self.assertIsInstance(email_msg, EmailMessage)
        self.assertEqual(email_msg.user, self.user)
        self.assertEqual(email_msg.subject, 'Test Email')
        self.assertEqual(email_msg.sender, 'sender@example.com')
        self.assertEqual(email_msg.recipients, ['test@example.com'])
        self.assertEqual(email_msg.message_id, 'test-message-123')
        self.assertEqual(email_msg.status, EmailStatus.FETCHED.value)

    def test_save_email_with_attachments(self):
        """Test email saving with attachments"""
        email_data = {
            'subject': 'Test Email with Attachments',
            'sender': 'sender@example.com',
            'recipients': ['test@example.com'],
            'received_at': timezone.now(),
            'raw_content': 'Raw email content',
            'html_content': '<p>HTML content</p>',
            'text_content': 'Text content',
            'message_id': 'test-message-456',
            'attachments': [
                {
                    'filename': 'test.pdf',
                    'content_type': 'application/pdf',
                    'file_size': 1024,
                    'file_path': '/tmp/test.pdf'
                }
            ]
        }

        with patch.object(self.service, 'process_attachments') as mock_process:
            email_msg = self.service.save_email(self.user.id, email_data)

            self.assertIsInstance(email_msg, EmailMessage)
            mock_process.assert_called_once_with(
                self.user.id, email_msg, email_data['attachments']
            )

    def test_save_email_exception(self):
        """Test email saving with exception"""
        email_data = {
            'subject': 'Test Email',
            'sender': 'sender@example.com',
            'recipients': ['test@example.com'],
            'received_at': timezone.now(),
            'raw_content': 'Raw email content',
            'message_id': 'test-message-789',
            'attachments': []
        }

        with patch('threadline.utils.email.service.EmailMessage.objects.create') as mock_create:
            mock_create.side_effect = Exception("Database error")

            with self.assertRaises(Exception):
                self.service.save_email(self.user.id, email_data)

    def test_find_user_by_recipient_email_match(self):
        """Test finding user by exact email match"""
        email_data = {
            'recipients': ['test@example.com']
        }

        user = self.service.find_user_by_recipient(email_data)
        self.assertEqual(user, self.user)

    def test_find_user_by_recipient_alias_match(self):
        """Test finding user by email alias match"""
        # Create email alias
        EmailAlias.objects.create(
            user=self.user,
            email_address='alias@example.com',
            is_active=True
        )

        email_data = {
            'recipients': ['alias@example.com']
        }

        user = self.service.find_user_by_recipient(email_data)
        self.assertEqual(user, self.user)

    def test_find_user_by_recipient_no_match(self):
        """Test finding user when no match found"""
        email_data = {
            'recipients': ['nonexistent@example.com']
        }

        user = self.service.find_user_by_recipient(email_data)
        self.assertIsNone(user)

    def test_find_user_by_recipient_no_recipients(self):
        """Test finding user when no recipients"""
        email_data = {
            'recipients': []
        }

        user = self.service.find_user_by_recipient(email_data)
        self.assertIsNone(user)

    def test_find_user_by_recipient_exception(self):
        """Test finding user with exception"""
        with patch('threadline.utils.email.service.User.objects.get') as mock_get:
            mock_get.side_effect = Exception("Database error")

            email_data = {
                'recipients': ['test@example.com']
            }

            user = self.service.find_user_by_recipient(email_data)
            self.assertIsNone(user)

    def test_cache_loading(self):
        """Test user cache loading"""
        # Create additional user and alias
        user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123'
        )

        EmailAlias.objects.create(
            user=user2,
            email_address='alias2@example.com',
            is_active=True
        )

        # Test cache loading
        self.service._load_user_cache()

        # Verify cache is loaded
        self.assertTrue(self.service._cache_loaded)
        self.assertIn('test@example.com', self.service._user_email_cache)
        self.assertIn('test2@example.com', self.service._user_email_cache)
        self.assertIn('alias2@example.com', self.service._alias_cache)

    def test_cache_refresh(self):
        """Test cache refresh functionality"""
        # Load initial cache
        self.service._load_user_cache()
        initial_cache_size = len(self.service._user_email_cache)

        # Refresh cache
        self.service.refresh_cache()

        # Verify cache is refreshed
        self.assertTrue(self.service._cache_loaded)
        self.assertEqual(len(self.service._user_email_cache), initial_cache_size)

    def test_process_attachments(self):
        """Test attachment processing"""
        email_msg = EmailMessage.objects.create(
            user=self.user,
            subject='Test',
            sender='test@example.com',
            recipients=['test@example.com'],
            received_at=timezone.now(),
            raw_content='test',
            message_id='test-123',
            status=EmailStatus.FETCHED.value
        )

        attachments = [
            {
                'filename': 'test.pdf',
                'safe_filename': 'test.pdf',
                'content_type': 'application/pdf',
                'file_size': 1024,
                'file_path': '/tmp/test.pdf',
                'is_image': False
            }
        ]

        with patch('threadline.utils.email.service.os.makedirs') as mock_makedirs, \
             patch('threadline.utils.email.service.shutil.move') as mock_move, \
             patch('threadline.utils.email.service.os.path.exists') as mock_exists, \
             patch('threadline.utils.email.service.EmailAttachment.objects.create') as mock_create:

            mock_exists.return_value = True
            mock_attachment = Mock()
            mock_create.return_value = mock_attachment

            result = self.service.process_attachments(
                self.user.id, email_msg, attachments
            )

            self.assertEqual(len(result), 1)
            mock_makedirs.assert_called_once()
            mock_move.assert_called_once()
            mock_create.assert_called_once()

    def test_process_attachments_exception(self):
        """Test attachment processing with exception"""
        email_msg = EmailMessage.objects.create(
            user=self.user,
            subject='Test',
            sender='test@example.com',
            recipients=['test@example.com'],
            received_at=timezone.now(),
            raw_content='test',
            message_id='test-456',
            status=EmailStatus.FETCHED.value
        )

        attachments = [
            {
                'filename': 'test.pdf',
                'file_path': '/tmp/test.pdf'
            }
        ]

        with patch('threadline.utils.email.service.os.makedirs') as mock_makedirs:
            mock_makedirs.side_effect = Exception("File system error")

            with self.assertRaises(Exception):
                self.service.process_attachments(
                    self.user.id, email_msg, attachments
                )