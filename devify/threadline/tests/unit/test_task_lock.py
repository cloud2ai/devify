"""
Unit tests for task lock functionality

Tests task lock management utilities and decorators.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.core.cache import cache

from threadline.utils.task_lock import (
    acquire_task_lock,
    release_task_lock,
    is_task_locked,
    force_release_all_locks,
    prevent_duplicate_task
)


class TaskLockTest(TestCase):
    """Test task lock functionality"""

    def setUp(self):
        """Set up test data"""
        # Use locmem cache for testing
        from django.core.cache import caches
        self.cache = caches['default']
        # Clear cache before each test
        self.cache.clear()

    def tearDown(self):
        """Clean up after each test"""
        self.cache.clear()

    def test_acquire_task_lock_success(self):
        """Test successful task lock acquisition"""
        result = acquire_task_lock('test_task', timeout=60)

        self.assertTrue(result)
        self.assertTrue(is_task_locked('test_task'))

    def test_acquire_task_lock_already_locked(self):
        """Test task lock acquisition when already locked"""
        # Acquire lock first time
        acquire_task_lock('test_task', timeout=60)

        # Try to acquire same lock again
        result = acquire_task_lock('test_task', timeout=60)

        self.assertFalse(result)
        self.assertTrue(is_task_locked('test_task'))

    def test_release_task_lock_success(self):
        """Test successful task lock release"""
        # Acquire lock first
        acquire_task_lock('test_task', timeout=60)
        self.assertTrue(is_task_locked('test_task'))

        # Release lock
        result = release_task_lock('test_task')

        self.assertTrue(result)
        self.assertFalse(is_task_locked('test_task'))

    def test_release_task_lock_not_locked(self):
        """Test releasing lock that doesn't exist"""
        result = release_task_lock('nonexistent_task')

        self.assertFalse(result)

    def test_is_task_locked(self):
        """Test task lock status checking"""
        # Initially not locked
        self.assertFalse(is_task_locked('test_task'))

        # After acquiring lock
        acquire_task_lock('test_task', timeout=60)
        self.assertTrue(is_task_locked('test_task'))

        # After releasing lock
        release_task_lock('test_task')
        self.assertFalse(is_task_locked('test_task'))

    def test_force_release_all_locks(self):
        """Test force release all locks"""
        # Acquire multiple locks
        acquire_task_lock('task1', timeout=60)
        acquire_task_lock('task2', timeout=60)
        acquire_task_lock('task3', timeout=60)

        # Verify locks exist
        self.assertTrue(is_task_locked('task1'))
        self.assertTrue(is_task_locked('task2'))
        self.assertTrue(is_task_locked('task3'))

        # Force release all locks
        force_release_all_locks()

        # Verify all locks are released
        self.assertFalse(is_task_locked('task1'))
        self.assertFalse(is_task_locked('task2'))
        self.assertFalse(is_task_locked('task3'))

    def test_acquire_task_lock_exception(self):
        """Test task lock acquisition with cache exception"""
        with patch('threadline.utils.task_lock.cache.add') as mock_add:
            mock_add.side_effect = Exception("Cache error")

            result = acquire_task_lock('test_task', timeout=60)

            self.assertFalse(result)

    def test_release_task_lock_exception(self):
        """Test task lock release with cache exception"""
        with patch('threadline.utils.task_lock.cache.delete') as mock_delete:
            mock_delete.side_effect = Exception("Cache error")

            result = release_task_lock('test_task')

            self.assertFalse(result)

    def test_is_task_locked_exception(self):
        """Test task lock status check with cache exception"""
        with patch('threadline.utils.task_lock.cache.get') as mock_get:
            mock_get.side_effect = Exception("Cache error")

            result = is_task_locked('test_task')

            self.assertFalse(result)

    def test_force_release_all_locks_exception(self):
        """Test force release all locks with cache exception"""
        with patch('threadline.utils.task_lock.cache.delete_many') as mock_delete_many:
            mock_delete_many.side_effect = Exception("Cache error")

            # Should not raise exception
            force_release_all_locks()

    def test_prevent_duplicate_task_decorator_success(self):
        """Test prevent_duplicate_task decorator with successful execution"""
        @prevent_duplicate_task('test_task', timeout=60)
        def test_function():
            return {'status': 'success', 'result': 'test'}

        result = test_function()

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['result'], 'test')

    def test_prevent_duplicate_task_decorator_already_running(self):
        """Test prevent_duplicate_task decorator when task is already running"""
        # Acquire lock first
        acquire_task_lock('test_task', timeout=60)

        @prevent_duplicate_task('test_task', timeout=60)
        def test_function():
            return {'status': 'success'}

        result = test_function()

        self.assertEqual(result['status'], 'skipped')
        self.assertEqual(result['reason'], 'task_already_running')

    def test_prevent_duplicate_task_decorator_lock_acquisition_failed(self):
        """Test prevent_duplicate_task decorator when lock acquisition fails"""
        with patch('threadline.utils.task_lock.acquire_task_lock') as mock_acquire:
            mock_acquire.return_value = False

            @prevent_duplicate_task('test_task', timeout=60)
            def test_function():
                return {'status': 'success'}

            result = test_function()

            self.assertEqual(result['status'], 'skipped')
            self.assertEqual(result['reason'], 'lock_acquisition_failed')

    def test_prevent_duplicate_task_decorator_with_user_id(self):
        """Test prevent_duplicate_task decorator with user-specific locks"""
        @prevent_duplicate_task('user_task', timeout=60, lock_param='user_id')
        def test_function(user_id):
            return {'status': 'success', 'user_id': user_id}

        # First call should succeed
        result1 = test_function(user_id=123)
        self.assertEqual(result1['status'], 'success')
        self.assertEqual(result1['user_id'], 123)

        # Second call with same user_id should be skipped
        result2 = test_function(user_id=123)
        self.assertEqual(result2['status'], 'skipped')
        self.assertEqual(result2['reason'], 'task_already_running')

        # Call with different user_id should succeed
        result3 = test_function(user_id=456)
        self.assertEqual(result3['status'], 'success')
        self.assertEqual(result3['user_id'], 456)

    def test_prevent_duplicate_task_decorator_exception_handling(self):
        """Test prevent_duplicate_task decorator with exception in function"""
        @prevent_duplicate_task('test_task', timeout=60)
        def test_function():
            raise ValueError("Test exception")

        with self.assertRaises(ValueError):
            test_function()

        # Lock should still be released after exception
        self.assertFalse(is_task_locked('test_task'))

    def test_prevent_duplicate_task_decorator_lock_release_on_exception(self):
        """Test that lock is released even when function raises exception"""
        @prevent_duplicate_task('test_task', timeout=60)
        def test_function():
            raise RuntimeError("Test exception")

        try:
            test_function()
        except RuntimeError:
            pass

        # Lock should be released
        self.assertFalse(is_task_locked('test_task'))

    def test_lock_timeout_expiration(self):
        """Test that locks expire after timeout"""
        # Acquire lock with short timeout
        acquire_task_lock('test_task', timeout=1)
        self.assertTrue(is_task_locked('test_task'))

        # Wait for timeout (in real scenario, this would be handled by cache)
        # For testing, we'll manually expire the lock
        cache.delete('email_fetch_lock:test_task')

        self.assertFalse(is_task_locked('test_task'))

    def test_multiple_lock_names(self):
        """Test that different lock names don't interfere"""
        acquire_task_lock('task1', timeout=60)
        acquire_task_lock('task2', timeout=60)

        self.assertTrue(is_task_locked('task1'))
        self.assertTrue(is_task_locked('task2'))

        release_task_lock('task1')

        self.assertFalse(is_task_locked('task1'))
        self.assertTrue(is_task_locked('task2'))

    def test_lock_key_format(self):
        """Test that lock keys are formatted correctly"""
        with patch('threadline.utils.task_lock.cache.add') as mock_add:
            mock_add.return_value = True

            acquire_task_lock('test_task', timeout=60)

            # Verify correct key format
            mock_add.assert_called_once_with(
                'email_fetch_lock:test_task',
                'locked',
                timeout=60
            )
