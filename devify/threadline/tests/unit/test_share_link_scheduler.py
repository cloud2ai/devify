"""
Unit tests for share link cleanup scheduler.
"""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from threadline.tasks.scheduler import schedule_share_link_cleanup


class ShareLinkSchedulerTest(TestCase):
    """Test the share link cleanup scheduler task."""

    @patch('threadline.utils.task_lock.release_task_lock')
    @patch('threadline.utils.task_lock.acquire_task_lock', return_value=True)
    @patch('threadline.utils.task_lock.is_task_locked', return_value=False)
    @patch('threadline.tasks.scheduler.ShareLinkCleanupManager')
    def test_schedule_share_link_cleanup_success(
        self,
        mock_manager,
        mock_is_locked,
        mock_acquire,
        mock_release
    ):
        """Scheduler should invoke cleanup manager and return its stats."""
        cleanup_stats = {
            'links_considered': 4,
            'links_deactivated': 4,
            'errors': 0
        }
        manager_instance = MagicMock()
        manager_instance.cleanup_expired_share_links.return_value = cleanup_stats
        mock_manager.return_value = manager_instance

        result = schedule_share_link_cleanup()

        self.assertEqual(result, cleanup_stats)
        manager_instance.cleanup_expired_share_links.assert_called_once()
        mock_is_locked.assert_called_once_with('share_link_cleanup')
        mock_acquire.assert_called_once_with('share_link_cleanup', 30)
        mock_release.assert_called_once_with('share_link_cleanup')

    @patch('threadline.utils.task_lock.release_task_lock')
    @patch('threadline.utils.task_lock.acquire_task_lock', return_value=True)
    @patch('threadline.utils.task_lock.is_task_locked', return_value=False)
    @patch('threadline.tasks.scheduler.ShareLinkCleanupManager')
    def test_schedule_share_link_cleanup_failure(
        self,
        mock_manager,
        mock_is_locked,
        mock_acquire,
        mock_release
    ):
        """Scheduler should re-raise errors from the cleanup manager."""
        manager_instance = MagicMock()
        manager_instance.cleanup_expired_share_links.side_effect = RuntimeError(
            'boom'
        )
        mock_manager.return_value = manager_instance

        with self.assertRaises(RuntimeError):
            schedule_share_link_cleanup()

        manager_instance.cleanup_expired_share_links.assert_called_once()
        mock_is_locked.assert_called_once_with('share_link_cleanup')
        mock_acquire.assert_called_once_with('share_link_cleanup', 30)
        mock_release.assert_called_once_with('share_link_cleanup')
