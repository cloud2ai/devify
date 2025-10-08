"""
Monitor Email Tasks Command

Management command for monitoring email task execution and metrics.
"""

import json
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from threadline.utils.monitoring import EmailTaskMonitor


class Command(BaseCommand):
    help = 'Monitor email task execution and display metrics'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help=(
                'Number of hours to look back for metrics '
                '(default: 24)'
            )
        )
        parser.add_argument(
            '--format',
            choices=['table', 'json', 'summary'],
            default='table',
            help='Output format (default: table)'
        )
        parser.add_argument(
            '--clear-cache',
            action='store_true',
            help='Clear metrics cache before generating report'
        )
        parser.add_argument(
            '--watch',
            action='store_true',
            help=(
                'Watch mode - continuously monitor and update display'
            )
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=30,
            help=(
                'Update interval in seconds for watch mode '
                '(default: 30)'
            )
        )

    def handle(self, *args, **options):
        """Handle the command execution"""
        try:
            hours = options['hours']
            output_format = options['format']
            clear_cache = options['clear_cache']
            watch_mode = options['watch']
            interval = options['interval']

            # Validate hours parameter
            if hours < 1 or hours > 168:
                raise CommandError(
                    'Hours must be between 1 and 168'
                )

            monitor = EmailTaskMonitor()

            if clear_cache:
                self.stdout.write('Clearing metrics cache...')
                monitor.clear_metrics_cache()
                self.stdout.write(
                    self.style.SUCCESS(
                        'Metrics cache cleared successfully'
                    )
                )

            if watch_mode:
                self._watch_mode(
                    monitor, hours, output_format, interval
                )
            else:
                self._generate_report(
                    monitor, hours, output_format
                )

        except Exception as e:
            raise CommandError(f'Error: {str(e)}')

    def _generate_report(self, monitor, hours, output_format):
        """Generate and display monitoring report"""
        try:
            # Get task metrics
            task_metrics = monitor.get_task_metrics(hours)

            # Get task status summary
            status_summary = monitor.get_task_status_summary()

            # Get email processing metrics
            email_metrics = monitor.get_email_processing_metrics(
                hours
            )

            if output_format == 'json':
                self._output_json(
                    task_metrics, status_summary, email_metrics
                )
            elif output_format == 'summary':
                self._output_summary(status_summary)
            else:
                self._output_table(
                    task_metrics, status_summary, email_metrics, hours
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f'Error generating report: {str(e)}'
                )
            )

    def _watch_mode(
        self, monitor, hours, output_format, interval
    ):
        """Watch mode - continuously monitor and update display"""
        import time

        self.stdout.write(
            self.style.SUCCESS(
                f'Starting watch mode (updating every {interval}s)...'
            )
        )
        self.stdout.write('Press Ctrl+C to stop\n')

        try:
            while True:
                # Clear screen (works on most terminals)
                self.stdout.write('\033[2J\033[H', ending='')

                # Generate and display report
                self._generate_report(
                    monitor, hours, output_format
                )

                # Wait for next update
                time.sleep(interval)

        except KeyboardInterrupt:
            self.stdout.write(
                '\n' + self.style.SUCCESS('Watch mode stopped')
            )

    def _output_json(
        self, task_metrics, status_summary, email_metrics
    ):
        """Output metrics in JSON format"""
        data = {
            'task_metrics': task_metrics,
            'status_summary': status_summary,
            'email_metrics': email_metrics,
            'generated_at': timezone.now().isoformat()
        }

        self.stdout.write(
            json.dumps(data, indent=2)
        )

    def _output_summary(self, status_summary):
        """Output brief status summary"""
        self.stdout.write(
            self.style.SUCCESS(
                '=== Email Task Status Summary ==='
            )
        )

        if 'error' in status_summary:
            self.stdout.write(
                self.style.ERROR(
                    f"Error: {status_summary['error']}"
                )
            )
            return

        # Display key metrics
        self.stdout.write(
            f"Running Tasks: {status_summary.get('running_tasks', 0)}"
        )
        self.stdout.write(
            f"Pending Tasks: {status_summary.get('pending_tasks', 0)}"
        )
        self.stdout.write(
            f"Stale Tasks: {status_summary.get('stale_tasks', 0)}"
        )
        self.stdout.write(
            f"Recent Failures: {status_summary.get('recent_failures', 0)}"
        )

        # Display status
        status = status_summary.get('status', 'unknown')
        if status == 'healthy':
            self.stdout.write(
                self.style.SUCCESS(
                    f"Overall Status: {status.upper()}"
                )
            )
        elif status == 'warning':
            self.stdout.write(
                self.style.WARNING(
                    f"Overall Status: {status.upper()}"
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    f"Overall Status: {status.upper()}"
                )
            )

    def _output_table(
        self, task_metrics, status_summary, email_metrics, hours
    ):
        """Output metrics in table format"""
        self.stdout.write(
            self.style.SUCCESS(
                f'=== Email Task Metrics (Last {hours} hours) ==='
            )
        )

        # Task Status Summary
        self.stdout.write('\n--- Task Status Summary ---')
        if 'error' in status_summary:
            self.stdout.write(
                self.style.ERROR(
                    f"Error: {status_summary['error']}"
                )
            )
        else:
            self.stdout.write(
                f"Running Tasks: {status_summary.get('running_tasks', 0)}"
            )
            self.stdout.write(
                f"Pending Tasks: {status_summary.get('pending_tasks', 0)}"
            )
            self.stdout.write(
                f"Stale Tasks: {status_summary.get('stale_tasks', 0)}"
            )
            self.stdout.write(
                f"Recent Failures: {status_summary.get('recent_failures', 0)}"
            )

            status = status_summary.get('status', 'unknown')
            status_style = (
                self.style.SUCCESS
                if status == 'healthy'
                else self.style.WARNING
            )
            self.stdout.write(
                f"Overall Status: {status_style(status.upper())}"
            )

        # Task Metrics
        self.stdout.write('\n--- Task Metrics ---')
        if 'error' in task_metrics:
            self.stdout.write(
                self.style.ERROR(
                    f"Error: {task_metrics['error']}"
                )
            )
        else:
            # Status counts
            self.stdout.write('\nStatus Distribution:')
            status_counts = task_metrics.get('status_counts', {})
            for status, count in status_counts.items():
                self.stdout.write(
                    f"  {status}: {count}"
                )

            # Performance metrics
            perf_metrics = task_metrics.get('performance_metrics', {})
            if perf_metrics:
                self.stdout.write('\nPerformance Metrics:')
                self.stdout.write(
                    f"  Avg Duration: "
                    f"{perf_metrics.get('avg_duration_seconds', 0):.2f}s"
                )
                self.stdout.write(
                    f"  Max Duration: "
                    f"{perf_metrics.get('max_duration_seconds', 0):.2f}s"
                )
                self.stdout.write(
                    f"  Avg Emails Processed: "
                    f"{perf_metrics.get('avg_emails_processed', 0):.2f}"
                )
                self.stdout.write(
                    f"  Total Emails Processed: "
                    f"{perf_metrics.get('total_emails_processed', 0)}"
                )

            # Error metrics
            error_metrics = task_metrics.get('error_metrics', {})
            if error_metrics:
                self.stdout.write('\nError Metrics:')
                self.stdout.write(
                    f"  Error Count: "
                    f"{error_metrics.get('error_count', 0)}"
                )
                self.stdout.write(
                    f"  Error Rate: "
                    f"{error_metrics.get('error_rate', 0):.2f}%"
                )

                common_errors = error_metrics.get('common_errors', [])
                if common_errors:
                    self.stdout.write("  Common Errors:")
                    for error, count in common_errors[:3]:
                        self.stdout.write(
                            f"    {error[:50]}... ({count})"
                        )

            # Source distribution
            source_dist = task_metrics.get('source_distribution', {})
            if source_dist:
                self.stdout.write('\nSource Distribution:')
                for source, count in source_dist.items():
                    self.stdout.write(
                        f"  {source}: {count}"
                    )

        # Email Processing Metrics
        self.stdout.write('\n--- Email Processing Metrics ---')
        if 'error' in email_metrics:
            self.stdout.write(
                self.style.ERROR(
                    f"Error: {email_metrics['error']}"
                )
            )
        else:
            email_counts = email_metrics.get('email_counts', {})
            if email_counts:
                self.stdout.write(
                    f"Total Emails: "
                    f"{email_counts.get('total_emails', 0)}"
                )
                self.stdout.write(
                    f"Unique Senders: "
                    f"{email_counts.get('unique_senders', 0)}"
                )
                self.stdout.write(
                    f"Unique Recipients: "
                    f"{email_counts.get('unique_recipients', 0)}"
                )

            status_dist = email_metrics.get('status_distribution', {})
            if status_dist:
                self.stdout.write('\nEmail Status Distribution:')
                for status, count in status_dist.items():
                    self.stdout.write(
                        f"  {status}: {count}"
                    )

        self.stdout.write(
            f'\nGenerated at: '
            f'{timezone.now().strftime("%Y-%m-%d %H:%M:%S")}'
        )
