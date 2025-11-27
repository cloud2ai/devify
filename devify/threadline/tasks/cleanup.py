"""
Email File Cleanup Tasks

Provides cleanup functionality for Haraka email files and EmailTask
records.

This module implements automated cleanup of email files from various
directories and EmailTask database records to prevent disk space issues
and maintain system performance.

File: devify/threadline/tasks/cleanup.py
"""

import logging
import os
from datetime import timedelta
from typing import Dict

from django.conf import settings
from django.utils import timezone

from threadline.models import EmailTask, ThreadlineShareLink
from threadline.utils.task_tracer import TaskTracer

logger = logging.getLogger(__name__)


class EmailCleanupManager:
    """
    Email file cleanup manager.

    Handles cleanup of email files from all directories and EmailTask
    records with proper configuration management and error handling.
    """

    def __init__(self):
        """Initialize the cleanup manager with configuration."""
        self.config = settings.EMAIL_CLEANUP_CONFIG
        self.base_dir = settings.HARAKA_EMAIL_BASE_DIR
        self.tracer = TaskTracer('HARAKA_CLEANUP')

    def cleanup_haraka_files(self) -> Dict:
        """
        Clean up Haraka email files from all directories.

        Returns:
            Dict containing cleanup statistics
        """
        stats = {
            'inbox_cleaned': 0,
            'processed_cleaned': 0,
            'failed_cleaned': 0,
            'errors': 0,
            'total_files_removed': 0,
            'total_size_freed': 0
        }

        inbox_stats = {'files_cleaned': 0, 'size_freed': 0, 'errors': 0}
        processed_stats = {'files_cleaned': 0, 'size_freed': 0, 'errors': 0}
        failed_stats = {'files_cleaned': 0, 'size_freed': 0, 'errors': 0}

        # Create task record at the beginning
        self.tracer.create_task(self._build_details_dict(
            stats, inbox_stats, processed_stats, failed_stats
        ))

        try:
            logger.info("Starting Haraka email files cleanup")

            # Clean up inbox directory
            inbox_stats = self._cleanup_directory(
                os.path.join(self.base_dir, 'inbox'),
                self.config['inbox_timeout_hours'] * 3600,
                'inbox'
            )
            stats['inbox_cleaned'] = inbox_stats['files_cleaned']
            stats['total_files_removed'] += inbox_stats['files_cleaned']
            stats['total_size_freed'] += inbox_stats['size_freed']
            stats['errors'] += inbox_stats['errors']
            # Update task with inbox progress
            self.tracer.update_task(
                self._build_details_dict(stats, inbox_stats,
                                        processed_stats, failed_stats)
            )

            # Clean up processed directory
            processed_stats = self._cleanup_directory(
                os.path.join(self.base_dir, 'processed'),
                self.config['processed_timeout_minutes'] * 60,
                'processed'
            )
            stats['processed_cleaned'] = processed_stats['files_cleaned']
            stats['total_files_removed'] += \
                processed_stats['files_cleaned']
            stats['total_size_freed'] += processed_stats['size_freed']
            stats['errors'] += processed_stats['errors']
            # Update task with processed progress
            self.tracer.update_task(
                self._build_details_dict(stats, inbox_stats,
                                        processed_stats, failed_stats)
            )

            # Clean up failed directory
            failed_stats = self._cleanup_directory(
                os.path.join(self.base_dir, 'failed'),
                self.config['failed_timeout_minutes'] * 60,
                'failed'
            )
            stats['failed_cleaned'] = failed_stats['files_cleaned']
            stats['total_files_removed'] += failed_stats['files_cleaned']
            stats['total_size_freed'] += failed_stats['size_freed']
            stats['errors'] += failed_stats['errors']

            # Final update: mark as completed
            details = self._build_details_dict(stats, inbox_stats,
                                              processed_stats, failed_stats)
            details['completed_at'] = timezone.now().isoformat()
            self.tracer.complete_task(details)

            logger.info(f"Haraka cleanup completed: {stats}")
            return stats

        except Exception as exc:
            logger.error(f"Haraka cleanup failed: {exc}")
            stats['errors'] += 1
            # Mark task as failed with current progress
            self.tracer.fail_task(
                self._build_details_dict(stats, inbox_stats,
                                        processed_stats, failed_stats),
                str(exc)
            )
            return stats


    def get_directory_stats(self, directory_path: str) -> Dict:
        """
        Get statistics for a directory.

        Args:
            directory_path: Path to directory to analyze

        Returns:
            Dict containing directory statistics
        """
        stats = {
            'file_count': 0,
            'total_size': 0,
            'meta_files': 0,
            'eml_files': 0,
            'orphaned_files': 0
        }

        if not os.path.exists(directory_path):
            return stats

        try:
            files = os.listdir(directory_path)

            # Count meta files and their corresponding eml files
            meta_files = [f for f in files if f.endswith('.meta')]
            eml_files = [f for f in files if f.endswith('.eml')]

            stats['meta_files'] = len(meta_files)
            stats['eml_files'] = len(eml_files)

            # Process meta files to get complete pairs
            for meta_file in meta_files:
                uuid = meta_file.replace('.meta', '')
                eml_file = f'{uuid}.eml'

                meta_path = os.path.join(directory_path, meta_file)
                eml_path = os.path.join(directory_path, eml_file)

                if os.path.exists(eml_path):
                    # Both files exist - count as a complete pair
                    stats['file_count'] += 1

                    # Add file sizes
                    stats['total_size'] += os.path.getsize(meta_path)
                    stats['total_size'] += os.path.getsize(eml_path)
                else:
                    # Orphaned meta file
                    stats['orphaned_files'] += 1
                    stats['total_size'] += os.path.getsize(meta_path)

            # Check for orphaned eml files
            for eml_file in eml_files:
                uuid = eml_file.replace('.eml', '')
                meta_file = f'{uuid}.meta'

                meta_file_path = os.path.join(directory_path, meta_file)
                if not os.path.exists(meta_file_path):
                    stats['orphaned_files'] += 1
                    stats['total_size'] += os.path.getsize(
                        os.path.join(directory_path, eml_file)
                    )

            return stats

        except Exception as e:
            logger.error(f"Error getting directory stats for "
                        f"{directory_path}: {e}")
            return stats

    def get_cleanup_stats(self) -> Dict:
        """
        Get comprehensive cleanup statistics for all directories.

        Returns:
            Dict containing statistics for all email directories
        """
        stats = {
            'inbox': self.get_directory_stats(
                os.path.join(self.base_dir, 'inbox')
            ),
            'processed': self.get_directory_stats(
                os.path.join(self.base_dir, 'processed')
            ),
            'failed': self.get_directory_stats(
                os.path.join(self.base_dir, 'failed')
            ),
            'total_files': 0,
            'total_size': 0
        }

        # Calculate totals
        for directory_stats in [stats['inbox'], stats['processed'],
                               stats['failed']]:
            stats['total_files'] += directory_stats['file_count']
            stats['total_size'] += directory_stats['total_size']

        return stats

    def _build_details_dict(self, total_stats: Dict, inbox_stats: Dict,
                           processed_stats: Dict,
                           failed_stats: Dict) -> Dict:
        """
        Build details dictionary for EmailTask record.

        Args:
            total_stats: Total cleanup statistics
            inbox_stats: Inbox directory statistics
            processed_stats: Processed directory statistics
            failed_stats: Failed directory statistics

        Returns:
            Details dictionary
        """
        return {
            'cleanup_type': 'HARAKA_CLEANUP',
            'total_files_removed': total_stats.get(
                'total_files_removed', 0
            ),
            'total_size_freed': total_stats.get('total_size_freed', 0),
            'total_errors': total_stats.get('errors', 0),
            'inbox': {
                'files_cleaned': inbox_stats.get('files_cleaned', 0),
                'size_freed': inbox_stats.get('size_freed', 0),
                'errors': inbox_stats.get('errors', 0)
            },
            'processed': {
                'files_cleaned': processed_stats.get('files_cleaned', 0),
                'size_freed': processed_stats.get('size_freed', 0),
                'errors': processed_stats.get('errors', 0)
            },
            'failed': {
                'files_cleaned': failed_stats.get('files_cleaned', 0),
                'size_freed': failed_stats.get('size_freed', 0),
                'errors': failed_stats.get('errors', 0)
            }
        }

    def _cleanup_directory(self, directory_path: str,
                            timeout_seconds: int,
                            directory_type: str) -> Dict:
        """
        Clean up files in a specific directory based on timeout.

        Args:
            directory_path: Path to directory to clean
            timeout_seconds: Files older than this many seconds will be
                deleted
            directory_type: Type of directory for logging
                            (inbox/processed/failed)

        Returns:
            Dict containing cleanup statistics for this directory
        """
        stats = {
            'files_cleaned': 0,
            'size_freed': 0,
            'errors': 0
        }

        if not os.path.exists(directory_path):
            logger.warning(f"Directory does not exist: {directory_path}")
            return stats

        try:
            current_time = timezone.now().timestamp()
            cutoff_time = current_time - timeout_seconds

            # Get all files in directory
            files = os.listdir(directory_path)
            if not files:
                logger.debug(f"No files found in {directory_type} "
                           f"directory")
                return stats

            # Process .meta files to get UUIDs
            meta_files = [f for f in files if f.endswith('.meta')]
            logger.info(f"Found {len(meta_files)} meta files in "
                        f"{directory_type} directory")

            for meta_file in meta_files:
                try:
                    uuid = meta_file.replace('.meta', '')
                    meta_path = os.path.join(directory_path, meta_file)
                    eml_path = os.path.join(directory_path,
                                           f'{uuid}.eml')

                    # Check if both files exist
                    if not os.path.exists(eml_path):
                        logger.warning(f"Missing .eml file: {uuid} in "
                                     f"{directory_type}")
                        continue

                    # Get file modification time
                    meta_mtime = os.path.getmtime(meta_path)
                    eml_mtime = os.path.getmtime(eml_path)

                    # Use the older of the two files as the reference
                    # time
                    file_time = min(meta_mtime, eml_mtime)

                    # Check if file is older than timeout
                    if file_time < cutoff_time:
                        # Calculate file sizes before deletion
                        meta_size = os.path.getsize(meta_path)
                        eml_size = os.path.getsize(eml_path)
                        total_size = meta_size + eml_size

                        # Delete both files
                        os.remove(meta_path)
                        os.remove(eml_path)

                        stats['files_cleaned'] += 1
                        stats['size_freed'] += total_size

                        logger.debug(f"Cleaned up {uuid} from "
                                   f"{directory_type} directory")

                except Exception as e:
                    logger.error(f"Error cleaning up {meta_file} in "
                               f"{directory_type}: {e}")
                    stats['errors'] += 1
                    continue

            logger.info(f"Cleaned {stats['files_cleaned']} files from "
                       f"{directory_type} directory")
            return stats

        except Exception as e:
            logger.error(f"Error cleaning {directory_type} directory: "
                        f"{e}")
            stats['errors'] += 1
            return stats


class EmailTaskCleanupManager:
    """
    EmailTask records cleanup manager.

    Handles cleanup of old EmailTask records from the database
    to prevent database bloat and maintain performance.
    """

    def __init__(self):
        """Initialize the cleanup manager with configuration."""
        self.config = settings.EMAIL_CLEANUP_CONFIG
        self.tracer = TaskTracer('TASK_CLEANUP')

    def cleanup_email_tasks(self) -> Dict:
        """
        Clean up old EmailTask records.

        Returns:
            Dict containing cleanup statistics
        """
        stats = {
            'tasks_cleaned': 0,
            'errors': 0
        }

        # Create task record
        self.tracer.create_task({
            'cleanup_type': 'TASK_CLEANUP',
            'tasks_cleaned': 0,
            'errors': 0
        })

        try:
            retention_days = self.config['email_task_retention_days']
            logger.info(f"Starting EmailTask cleanup (retention: "
                       f"{retention_days} days)")

            # Calculate cutoff date
            cutoff_date = timezone.now() - timedelta(days=retention_days)

            # Get old tasks
            old_tasks = EmailTask.objects.filter(
                created_at__lt=cutoff_date
            )

            task_count = old_tasks.count()
            logger.info(f"Found {task_count} old EmailTask records to "
                       f"clean up")

            if task_count > 0:
                # Delete in batches to avoid memory issues
                batch_size = 1000
                deleted_count = 0

                while True:
                    batch = old_tasks[:batch_size]
                    if not batch:
                        break

                    batch_ids = [task.id for task in batch]
                    deleted, _ = EmailTask.objects.filter(
                        id__in=batch_ids
                    ).delete()

                    deleted_count += deleted
                    logger.debug(f"Deleted batch of {deleted} EmailTask "
                               f"records")

                stats['tasks_cleaned'] = deleted_count
                logger.info(f"Cleaned up {deleted_count} EmailTask "
                           f"records")

            # Complete task record
            details = {
                'cleanup_type': 'TASK_CLEANUP',
                'tasks_cleaned': stats['tasks_cleaned'],
                'errors': stats['errors'],
                'completed_at': timezone.now().isoformat()
            }
            self.tracer.complete_task(details)

            return stats

        except Exception as e:
            logger.error(f"EmailTask cleanup failed: {e}")
            stats['errors'] += 1
            details = {
                'cleanup_type': 'TASK_CLEANUP',
                'tasks_cleaned': stats['tasks_cleaned'],
                'errors': stats['errors']
            }
            self.tracer.fail_task(details, str(e))
            return stats


class ShareLinkCleanupManager:
    """
    Cleanup manager for Threadline share links.

    Deactivates share links that are past their expiry time to
    prevent stale or unsafe public URLs from remaining active.
    """

    def __init__(self):
        """Initialize share link cleanup configuration."""
        config = getattr(settings, 'SHARE_LINK_CLEANUP_CONFIG', {})
        self.grace_period_minutes = config.get('grace_period_minutes', 0)
        self.batch_size = config.get('batch_size', 500)
        self.tracer = TaskTracer('SHARE_LINK_CLEANUP')

    def cleanup_expired_share_links(self) -> Dict:
        """
        Deactivate all share links that have passed their expiration time.

        Returns:
            Dict containing cleanup statistics
        """
        stats = {
            'links_considered': 0,
            'links_deactivated': 0,
            'errors': 0
        }

        now = timezone.now()
        cutoff = now - timedelta(minutes=self.grace_period_minutes)

        base_filters = {
            'is_active': True,
            'expires_at__isnull': False,
            'expires_at__lt': cutoff
        }

        expired_queryset = ThreadlineShareLink.objects.filter(
            **base_filters
        )
        stats['links_considered'] = expired_queryset.count()

        task_details = {
            'cleanup_type': 'SHARE_LINK_CLEANUP',
            'links_considered': stats['links_considered'],
            'links_deactivated': 0,
            'grace_period_minutes': self.grace_period_minutes,
            'batch_size': self.batch_size
        }
        self.tracer.create_task(task_details.copy())

        if stats['links_considered'] == 0:
            task_details.update({'completed_at': now.isoformat()})
            self.tracer.complete_task(task_details)
            logger.info("Share link cleanup: no expired links found.")
            return stats

        try:
            while True:
                batch_queryset = ThreadlineShareLink.objects.filter(
                    **base_filters
                ).order_by('expires_at')[:self.batch_size]
                batch_ids = list(batch_queryset.values_list('id', flat=True))

                if not batch_ids:
                    break

                deactivated = ThreadlineShareLink.objects.filter(
                    id__in=batch_ids
                ).update(is_active=False, updated_at=now)

                stats['links_deactivated'] += deactivated

                task_details.update({
                    'links_deactivated': stats['links_deactivated']
                })
                self.tracer.update_task(task_details.copy())

            task_details.update({
                'links_deactivated': stats['links_deactivated'],
                'completed_at': timezone.now().isoformat()
            })
            self.tracer.complete_task(task_details)

            logger.info(
                "Share link cleanup completed. "
                f"Deactivated {stats['links_deactivated']} expired links."
            )
            return stats

        except Exception as exc:
            stats['errors'] += 1
            task_details.update({
                'links_deactivated': stats['links_deactivated'],
                'error': str(exc)
            })
            self.tracer.fail_task(task_details, str(exc))
            logger.error(f"Share link cleanup failed: {exc}")
            return stats
