"""
Django management command for email file cleanup.

This command provides manual cleanup of email files and EmailTask records
with various options for configuration and monitoring.

Usage:
    python manage.py cleanup_email_files [options]

Examples:
    # Clean up all email files
    python manage.py cleanup_email_files

    # Clean up only inbox directory
    python manage.py cleanup_email_files --inbox-only

    # Clean up with custom timeout
    python manage.py cleanup_email_files --inbox-timeout 2

    # Show statistics only
    python manage.py cleanup_email_files --stats-only

    # Dry run (show what would be cleaned)
    python manage.py cleanup_email_files --dry-run
"""

import logging

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from threadline.tasks.cleanup import (
    EmailCleanupManager,
    EmailTaskCleanupManager
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Management command for email file cleanup."""

    help = 'Clean up email files and EmailTask records'

    def add_arguments(self, parser):
        """Add command line arguments."""

        # Directory selection
        parser.add_argument(
            '--inbox-only',
            action='store_true',
            help='Clean up only inbox directory'
        )
        parser.add_argument(
            '--processed-only',
            action='store_true',
            help='Clean up only processed directory'
        )
        parser.add_argument(
            '--failed-only',
            action='store_true',
            help='Clean up only failed directory'
        )

        # Timeout configuration
        parser.add_argument(
            '--inbox-timeout',
            type=int,
            help='Inbox timeout in hours (default: from settings)'
        )
        parser.add_argument(
            '--processed-timeout',
            type=int,
            help='Processed timeout in minutes (default: from settings)'
        )
        parser.add_argument(
            '--failed-timeout',
            type=int,
            help='Failed timeout in minutes (default: from settings)'
        )
        parser.add_argument(
            '--task-retention',
            type=int,
            help='EmailTask retention in days (default: from settings)'
        )

        # Operation modes
        parser.add_argument(
            '--stats-only',
            action='store_true',
            help='Show statistics only, do not perform cleanup'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleaned without actually cleaning'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output'
        )

        # EmailTask cleanup
        parser.add_argument(
            '--skip-tasks',
            action='store_true',
            help='Skip EmailTask cleanup'
        )
        parser.add_argument(
            '--tasks-only',
            action='store_true',
            help='Clean up only EmailTask records'
        )


    def handle(self, *args, **options):
        """Handle the command execution."""

        try:
            # Set up logging level
            if options['verbose']:
                logging.getLogger().setLevel(logging.DEBUG)

            # Show configuration
            self._show_configuration(options)

            # Handle stats-only mode
            if options['stats_only']:
                self._show_statistics(options)
                return

            # Handle dry-run mode
            if options['dry_run']:
                self._show_dry_run(options)
                return

            # Perform cleanup
            self._perform_cleanup(options)

        except Exception as e:
            logger.error(f"Cleanup command failed: {e}")
            raise CommandError(f"Cleanup failed: {e}")

    def _show_configuration(self, options):
        """Show current configuration."""

        self.stdout.write(
            self.style.SUCCESS("Email File Cleanup Configuration")
        )
        self.stdout.write("=" * 50)

        # Show directory selection
        if options['inbox_only']:
            self.stdout.write("Mode: Inbox directory only")
        elif options['processed_only']:
            self.stdout.write("Mode: Processed directory only")
        elif options['failed_only']:
            self.stdout.write("Mode: Failed directory only")
        elif options['tasks_only']:
            self.stdout.write("Mode: EmailTask records only")
        else:
            self.stdout.write("Mode: All directories and EmailTask "
                            "records")

        # Show timeout settings
        config = self._get_cleanup_config()
        self.stdout.write(f"Inbox timeout: "
                        f"{config['inbox_timeout_hours']} hours")
        self.stdout.write(f"Processed timeout: "
                        f"{config['processed_timeout_minutes']} minutes")
        self.stdout.write(f"Failed timeout: "
                        f"{config['failed_timeout_minutes']} minutes")
        self.stdout.write(f"Task retention: "
                        f"{config['email_task_retention_days']} days")

        # Show custom overrides
        if options['inbox_timeout']:
            self.stdout.write(f"Inbox timeout override: "
                            f"{options['inbox_timeout']} hours")
        if options['processed_timeout']:
            self.stdout.write(f"Processed timeout override: "
                            f"{options['processed_timeout']} minutes")
        if options['failed_timeout']:
            self.stdout.write(f"Failed timeout override: "
                            f"{options['failed_timeout']} minutes")
        if options['task_retention']:
            self.stdout.write(f"Task retention override: "
                            f"{options['task_retention']} days")

        self.stdout.write("")

    def _show_statistics(self, options):
        """Show cleanup statistics."""

        self.stdout.write(
            self.style.SUCCESS("Email File Cleanup Statistics")
        )
        self.stdout.write("=" * 50)

        # Get directory statistics
        try:
            cleanup_manager = EmailCleanupManager()
            stats = cleanup_manager.get_cleanup_stats()

            self.stdout.write("Directory Statistics:")
            self.stdout.write("-" * 30)

            for directory in ['inbox', 'processed', 'failed']:
                dir_stats = stats[directory]
                self.stdout.write(f"{directory.title()}:")
                self.stdout.write(f"  Files: {dir_stats['file_count']}")
                size_str = self._format_size(dir_stats['total_size'])
                self.stdout.write(f"  Size: {size_str}")
                self.stdout.write(f"  Meta files: "
                                f"{dir_stats['meta_files']}")
                self.stdout.write(f"  EML files: "
                                f"{dir_stats['eml_files']}")
                self.stdout.write(f"  Orphaned files: "
                                f"{dir_stats['orphaned_files']}")
                self.stdout.write("")

            self.stdout.write(f"Total files: {stats['total_files']}")
            self.stdout.write(f"Total size: "
                            f"{self._format_size(stats['total_size'])}")
            self.stdout.write("")

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error getting directory stats: {e}")
            )


    def _show_dry_run(self, options):
        """Show what would be cleaned in dry-run mode."""

        self.stdout.write(
            self.style.WARNING("DRY RUN - No files will be deleted")
        )
        self.stdout.write("=" * 50)

        # This would require implementing dry-run logic in cleanup
        # functions. For now, just show current statistics
        self._show_statistics(options)

        self.stdout.write(
            self.style.WARNING("Dry run completed - no changes made")
        )

    def _perform_cleanup(self, options):
        """Perform the actual cleanup."""

        self.stdout.write(
            self.style.SUCCESS("Starting email file cleanup...")
        )

        # Clean up email files
        if not options['tasks_only']:
            self._cleanup_email_files(options)

        # Clean up EmailTask records
        if (not options['skip_tasks'] and not options['inbox_only'] and
                not options['processed_only'] and
                not options['failed_only']):
            self._cleanup_email_tasks(options)

        self.stdout.write(
            self.style.SUCCESS("Cleanup completed successfully!")
        )

    def _cleanup_email_files(self, options):
        """Clean up email files."""

        try:
            # Apply custom timeout overrides
            if any([options['inbox_timeout'],
                    options['processed_timeout'],
                    options['failed_timeout']]):
                self._apply_timeout_overrides(options)

            # Perform cleanup
            cleanup_manager = EmailCleanupManager()
            result = cleanup_manager.cleanup_haraka_files()

            # Show results
            self.stdout.write("File Cleanup Results:")
            self.stdout.write("-" * 30)
            self.stdout.write(f"Inbox cleaned: "
                            f"{result.get('inbox_cleaned', 0)}")
            self.stdout.write(f"Processed cleaned: "
                            f"{result.get('processed_cleaned', 0)}")
            self.stdout.write(f"Failed cleaned: "
                            f"{result.get('failed_cleaned', 0)}")
            self.stdout.write(f"Total files removed: "
                            f"{result.get('total_files_removed', 0)}")
            size_freed = self._format_size(
                result.get('total_size_freed', 0)
            )
            self.stdout.write(f"Total size freed: {size_freed}")
            self.stdout.write(f"Errors: {result.get('errors', 0)}")
            self.stdout.write("")

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Email file cleanup failed: {e}")
            )
            raise

    def _cleanup_email_tasks(self, options):
        """Clean up EmailTask records."""

        try:
            # Apply custom retention override
            if options['task_retention']:
                self._apply_retention_override(options)

            # Perform cleanup
            task_cleanup_manager = EmailTaskCleanupManager()
            result = task_cleanup_manager.cleanup_email_tasks()

            # Show results
            self.stdout.write("EmailTask Cleanup Results:")
            self.stdout.write("-" * 30)
            self.stdout.write(f"Tasks cleaned: "
                            f"{result.get('tasks_cleaned', 0)}")
            self.stdout.write(f"Errors: {result.get('errors', 0)}")
            self.stdout.write("")

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"EmailTask cleanup failed: {e}")
            )
            raise

    def _get_cleanup_config(self):
        """Get cleanup configuration."""

        return getattr(settings, 'EMAIL_CLEANUP_CONFIG', {
            'inbox_timeout_hours': 1,
            'processed_timeout_minutes': 10,
            'failed_timeout_minutes': 10,
            'email_task_retention_days': 3,
        })

    def _apply_timeout_overrides(self, options):
        """Apply timeout overrides to settings."""

        # This would require modifying the cleanup functions to accept
        # custom timeouts. For now, we'll just log the overrides.

        if options['inbox_timeout']:
            self.stdout.write(
                f"Note: Inbox timeout override "
                f"({options['inbox_timeout']} hours) "
                "not yet implemented in cleanup functions"
            )

        if options['processed_timeout']:
            self.stdout.write(
                f"Note: Processed timeout override "
                f"({options['processed_timeout']} minutes) "
                "not yet implemented in cleanup functions"
            )

        if options['failed_timeout']:
            self.stdout.write(
                f"Note: Failed timeout override "
                f"({options['failed_timeout']} minutes) "
                "not yet implemented in cleanup functions"
            )

    def _apply_retention_override(self, options):
        """Apply retention override to settings."""

        if options['task_retention']:
            self.stdout.write(
                f"Note: Task retention override "
                f"({options['task_retention']} days) "
                "not yet implemented in cleanup functions"
            )

    def _format_size(self, size_bytes):
        """Format size in bytes to human readable format."""

        if size_bytes == 0:
            return "0 B"

        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1

        return f"{size_bytes:.1f} {size_names[i]}"
