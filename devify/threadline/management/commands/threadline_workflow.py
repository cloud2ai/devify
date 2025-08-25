"""
Threadline Workflow CLI - Comprehensive workflow testing and management tool.
"""
import logging
import time
import json
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.db import transaction

from threadline.models import EmailMessage, EmailAttachment, Settings, JiraIssue
from threadline.state_machine import EmailStatus, AttachmentStatus
from threadline.tasks import (
    scan_user_emails,
    ocr_images_for_email,
    organize_email_body_task,
    organize_attachments_ocr_task,
    summarize_email_task,
    submit_issue_to_jira,
    process_email_chain
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Threadline Workflow CLI - Comprehensive workflow testing and management tool.
    """
    help = 'Threadline workflow CLI for testing and managing email processing workflows'

    def add_arguments(self, parser):
        # Main action
        parser.add_argument(
            'action',
            choices=[
                'config',      # Test configuration
                'scan',        # Test email scanning
                'process',     # Test single email processing
                'workflow',    # Test complete workflow
                'status',      # Show system status
                'cleanup',     # Cleanup test data
                'benchmark',   # Performance benchmarking
                'health',      # Health check
            ],
            help='Test action to perform'
        )

        # User specification
        parser.add_argument(
            '--user',
            type=str,
            help='Username to test (required for most actions)'
        )

        # Email specification
        parser.add_argument(
            '--email-id',
            type=int,
            help='Specific email ID to test'
        )

        # Test options
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force reprocessing, ignore current status'
        )

        parser.add_argument(
            '--async',
            action='store_true',
            help='Run tasks asynchronously (default: synchronous for testing)'
        )

        parser.add_argument(
            '--timeout',
            type=int,
            default=30,
            help='Task timeout in seconds (default: 30)'
        )

        # Output options
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output'
        )

        parser.add_argument(
            '--json',
            action='store_true',
            help='Output results in JSON format'
        )

        parser.add_argument(
            '--quiet',
            action='store_true',
            help='Minimal output (errors only)'
        )

        # Filter options
        parser.add_argument(
            '--limit',
            type=int,
            default=10,
            help='Limit number of items to process/display'
        )

        parser.add_argument(
            '--status-filter',
            choices=[status.value for status in EmailStatus],
            help='Filter emails by status'
        )

    def handle(self, *args, **options):
        self.options = options
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'action': options['action'],
            'success': False,
            'data': {},
            'errors': []
        }

        try:
            action = options['action']

            if action == 'config':
                self.test_configuration()
            elif action == 'scan':
                self.test_email_scanning()
            elif action == 'process':
                self.test_email_processing()
            elif action == 'workflow':
                self.test_complete_workflow()
            elif action == 'status':
                self.show_system_status()
            elif action == 'cleanup':
                self.cleanup_test_data()
            elif action == 'benchmark':
                self.run_benchmark()
            elif action == 'health':
                self.health_check()

            self.results['success'] = True

        except Exception as e:
            self.results['errors'].append(str(e))
            if not self.options['quiet']:
                self.stdout.write(
                    self.style.ERROR(f"❌ Test failed: {e}")
                )

        finally:
            self.output_results()

    def test_configuration(self):
        """Test user configuration and settings."""
        user = self.get_required_user()
        self.log_info(f"🔧 Testing configuration for user: {user.username}")

        config_results = {
            'user': user.username,
            'configs': {},
            'missing_configs': [],
            'invalid_configs': []
        }

        required_configs = ['email_config', 'jira_config', 'prompt_config']
        optional_configs = ['email_filter_config']

        for config_key in required_configs + optional_configs:
            try:
                setting = Settings.objects.filter(
                    user=user,
                    key=config_key,
                    is_active=True
                ).first()

                if setting:
                    # Validate JSON
                    try:
                        config_data = json.loads(setting.value)
                        config_results['configs'][config_key] = {
                            'status': 'valid',
                            'fields': list(config_data.keys()) if isinstance(config_data, dict) else 'non-dict'
                        }
                        self.log_success(f"✓ {config_key}: Valid")
                    except json.JSONDecodeError:
                        config_results['invalid_configs'].append(config_key)
                        self.log_error(f"✗ {config_key}: Invalid JSON")
                else:
                    if config_key in required_configs:
                        config_results['missing_configs'].append(config_key)
                        self.log_error(f"✗ {config_key}: Missing")
                    else:
                        self.log_warning(f"⚠ {config_key}: Optional, not configured")

            except Exception as e:
                config_results['invalid_configs'].append(config_key)
                self.log_error(f"✗ {config_key}: Error - {e}")

        self.results['data'] = config_results

    def test_email_scanning(self):
        """Test email scanning functionality."""
        user = self.get_required_user()
        self.log_info(f"📧 Testing email scanning for user: {user.username}")

        # Check email config first
        email_config = Settings.objects.filter(
            user=user, key='email_config', is_active=True
        ).first()

        if not email_config:
            raise CommandError("No active email_config found for user")

        # Count emails before scan
        emails_before = EmailMessage.objects.filter(user=user).count()

        # Run scan
        if self.options['async']:
            result = scan_user_emails.delay(user.id)
            self.log_info(f"📤 Scan task queued: {result.id}")

            if self.options['timeout'] > 0:
                try:
                    task_result = result.get(timeout=self.options['timeout'])
                    self.log_success(f"✓ Scan completed: {task_result}")
                except Exception as e:
                    raise CommandError(f"Scan task failed: {e}")
        else:
            # Synchronous execution for testing
            task_result = scan_user_emails.run(user.id)
            self.log_success(f"✓ Scan completed: {task_result}")

        # Count emails after scan
        emails_after = EmailMessage.objects.filter(user=user).count()
        new_emails = emails_after - emails_before

        self.results['data'] = {
            'user': user.username,
            'emails_before': emails_before,
            'emails_after': emails_after,
            'new_emails': new_emails,
            'task_result': str(task_result)
        }

        self.log_info(f"📊 Scan results: {new_emails} new emails found")

    def test_email_processing(self):
        """Test individual email processing steps."""
        user = self.get_required_user()
        email_id = self.options.get('email_id')

        if email_id:
            try:
                email = EmailMessage.objects.get(id=email_id, user=user)
            except EmailMessage.DoesNotExist:
                raise CommandError(f"Email {email_id} not found for user {user.username}")
        else:
            # Get latest email
            email = EmailMessage.objects.filter(user=user).order_by('-id').first()
            if not email:
                raise CommandError(f"No emails found for user {user.username}")

        self.log_info(f"🔄 Testing email processing for ID: {email.id}")
        self.log_info(f"📝 Subject: {email.subject[:60]}...")

        processing_results = {
            'email_id': email.id,
            'initial_status': email.status,
            'steps': {},
            'final_status': None,
            'attachments': []
        }

        force = self.options['force']
        async_mode = self.options['async']
        timeout = self.options['timeout']

        # Processing steps
        steps = [
            ('OCR', ocr_images_for_email),
            ('Email Body Organization', organize_email_body_task),
            ('Attachment Organization', organize_attachments_ocr_task),
            ('Summarization', summarize_email_task),
            ('JIRA Submission', submit_issue_to_jira)
        ]

        for step_name, task_func in steps:
            self.log_info(f"🔧 Testing {step_name}...")

            try:
                if async_mode:
                    result = task_func.delay(email.id, force)
                    self.log_info(f"   📤 Task queued: {result.id}")

                    if timeout > 0:
                        task_result = result.get(timeout=timeout)
                        processing_results['steps'][step_name] = {
                            'status': 'completed',
                            'task_id': result.id,
                            'result': str(task_result)
                        }
                        self.log_success(f"   ✓ {step_name} completed")
                    else:
                        processing_results['steps'][step_name] = {
                            'status': 'queued',
                            'task_id': result.id
                        }
                else:
                    # Synchronous for testing
                    task_result = task_func.run(email.id, force)
                    processing_results['steps'][step_name] = {
                        'status': 'completed',
                        'result': str(task_result)
                    }
                    self.log_success(f"   ✓ {step_name} completed")

            except Exception as e:
                processing_results['steps'][step_name] = {
                    'status': 'failed',
                    'error': str(e)
                }
                self.log_error(f"   ✗ {step_name} failed: {e}")

        # Refresh email status
        email.refresh_from_db()
        processing_results['final_status'] = email.status

        # Get attachment info
        for att in email.attachments.all():
            processing_results['attachments'].append({
                'id': att.id,
                'filename': att.filename,
                'status': att.status,
                'is_image': att.is_image
            })

        self.results['data'] = processing_results
        self.log_info(f"📊 Final email status: {email.status}")

    def test_complete_workflow(self):
        """Test complete workflow using processing chain."""
        user = self.get_required_user()
        email_id = self.options.get('email_id')

        if email_id:
            try:
                email = EmailMessage.objects.get(id=email_id, user=user)
            except EmailMessage.DoesNotExist:
                raise CommandError(f"Email {email_id} not found for user {user.username}")
        else:
            # Get latest email
            email = EmailMessage.objects.filter(user=user).order_by('-id').first()
            if not email:
                raise CommandError(f"No emails found for user {user.username}")

        self.log_info(f"⛓️ Testing complete workflow for email ID: {email.id}")

        initial_status = email.status
        force = self.options['force']
        timeout = self.options['timeout']

        # Run processing chain
        if self.options['async']:
            result = process_email_chain.delay(email.id, force)
            self.log_info(f"📤 Processing chain queued: {result.id}")

            if timeout > 0:
                try:
                    task_result = result.get(timeout=timeout)
                    self.log_success(f"✓ Workflow completed: {task_result}")
                except Exception as e:
                    raise CommandError(f"Workflow failed: {e}")
        else:
            task_result = process_email_chain.run(email.id, force)
            self.log_success(f"✓ Workflow completed: {task_result}")

        # Refresh and check final status
        email.refresh_from_db()

        workflow_results = {
            'email_id': email.id,
            'initial_status': initial_status,
            'final_status': email.status,
            'has_llm_content': bool(email.llm_content),
            'has_summary': bool(email.summary_content and email.summary_title),
            'attachments_processed': email.attachments.filter(
                status=AttachmentStatus.LLM_SUCCESS.value
            ).count(),
            'total_attachments': email.attachments.count(),
            'jira_created': bool(hasattr(email, 'jira_issue') and email.jira_issue)
        }

        self.results['data'] = workflow_results

    def show_system_status(self):
        """Show comprehensive system status."""
        user = self.get_user_if_provided()

        self.log_info("📊 System Status Report")

        status_data = {
            'users': {},
            'emails': {},
            'attachments': {},
            'jira_issues': {}
        }

        if user:
            # User-specific status
            users_query = User.objects.filter(id=user.id)
            emails_query = EmailMessage.objects.filter(user=user)
        else:
            # System-wide status
            users_query = User.objects.all()
            emails_query = EmailMessage.objects.all()

        # User statistics
        status_data['users']['total'] = users_query.count()
        status_data['users']['with_email_config'] = users_query.filter(
            settings__key='email_config', settings__is_active=True
        ).distinct().count()

        # Email statistics
        status_data['emails']['total'] = emails_query.count()
        for status in EmailStatus:
            count = emails_query.filter(status=status.value).count()
            if count > 0:
                status_data['emails'][status.value] = count

        # Attachment statistics
        if user:
            attachments_query = EmailAttachment.objects.filter(email_message__user=user)
        else:
            attachments_query = EmailAttachment.objects.all()

        status_data['attachments']['total'] = attachments_query.count()
        status_data['attachments']['images'] = attachments_query.filter(is_image=True).count()

        for status in AttachmentStatus:
            count = attachments_query.filter(status=status.value).count()
            if count > 0:
                status_data['attachments'][status.value] = count

        # JIRA statistics
        if user:
            jira_query = JiraIssue.objects.filter(email_message__user=user)
        else:
            jira_query = JiraIssue.objects.all()

        status_data['jira_issues']['total'] = jira_query.count()

        self.results['data'] = status_data

        if not self.options['json'] and not self.options['quiet']:
            self.print_status_summary(status_data, user)

    def cleanup_test_data(self):
        """Cleanup test data (use with caution)."""
        user = self.get_user_if_provided()

        if not user:
            raise CommandError("User must be specified for cleanup action")

        self.log_warning(f"🧹 Cleaning up test data for user: {user.username}")

        with transaction.atomic():
            # Delete JIRA issues
            jira_count = JiraIssue.objects.filter(email_message__user=user).count()
            JiraIssue.objects.filter(email_message__user=user).delete()

            # Delete attachments
            attachment_count = EmailAttachment.objects.filter(email_message__user=user).count()
            EmailAttachment.objects.filter(email_message__user=user).delete()

            # Delete emails
            email_count = EmailMessage.objects.filter(user=user).count()
            EmailMessage.objects.filter(user=user).delete()

        cleanup_results = {
            'user': user.username,
            'deleted_emails': email_count,
            'deleted_attachments': attachment_count,
            'deleted_jira_issues': jira_count
        }

        self.results['data'] = cleanup_results
        self.log_success(f"✓ Cleanup completed: {email_count} emails, {attachment_count} attachments, {jira_count} JIRA issues")

    def run_benchmark(self):
        """Run performance benchmarking."""
        user = self.get_required_user()

        self.log_info(f"⏱️ Running benchmark for user: {user.username}")

        # Get sample emails
        emails = EmailMessage.objects.filter(user=user)[:self.options['limit']]

        if not emails:
            raise CommandError("No emails found for benchmarking")

        benchmark_results = {
            'user': user.username,
            'email_count': len(emails),
            'timing': {},
            'errors': []
        }

        for email in emails:
            self.log_info(f"📊 Benchmarking email {email.id}...")

            start_time = time.time()
            try:
                # Run chain synchronously for accurate timing
                process_email_chain.run(email.id, force=True)
                end_time = time.time()

                processing_time = end_time - start_time
                benchmark_results['timing'][email.id] = processing_time

                self.log_success(f"   ✓ Completed in {processing_time:.2f}s")

            except Exception as e:
                benchmark_results['errors'].append({
                    'email_id': email.id,
                    'error': str(e)
                })
                self.log_error(f"   ✗ Failed: {e}")

        # Calculate statistics
        if benchmark_results['timing']:
            times = list(benchmark_results['timing'].values())
            benchmark_results['statistics'] = {
                'avg_time': sum(times) / len(times),
                'min_time': min(times),
                'max_time': max(times),
                'total_time': sum(times)
            }

        self.results['data'] = benchmark_results

    def health_check(self):
        """Perform system health check."""
        self.log_info("🏥 Performing health check...")

        health_data = {
            'database': self.check_database(),
            'celery': self.check_celery(),
            'redis': self.check_redis(),
            'configurations': self.check_configurations()
        }

        self.results['data'] = health_data

    # Helper methods
    def get_required_user(self):
        """Get user from options, raise error if not provided."""
        username = self.options.get('user')
        if not username:
            raise CommandError("--user is required for this action")

        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"User '{username}' does not exist")

    def get_user_if_provided(self):
        """Get user from options if provided, return None otherwise."""
        username = self.options.get('user')
        if username:
            try:
                return User.objects.get(username=username)
            except User.DoesNotExist:
                raise CommandError(f"User '{username}' does not exist")
        return None

    def log_info(self, message):
        """Log info message."""
        if not self.options['quiet']:
            self.stdout.write(message)

    def log_success(self, message):
        """Log success message."""
        if not self.options['quiet']:
            self.stdout.write(self.style.SUCCESS(message))

    def log_warning(self, message):
        """Log warning message."""
        if not self.options['quiet']:
            self.stdout.write(self.style.WARNING(message))

    def log_error(self, message):
        """Log error message."""
        self.stdout.write(self.style.ERROR(message))

    def check_database(self):
        """Check database connectivity."""
        try:
            User.objects.count()
            return {'status': 'healthy', 'message': 'Database connection OK'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def check_celery(self):
        """Check Celery connectivity."""
        try:
            from celery import current_app
            inspect = current_app.control.inspect()
            stats = inspect.stats()
            if stats:
                return {'status': 'healthy', 'workers': len(stats)}
            else:
                return {'status': 'warning', 'message': 'No workers available'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def check_redis(self):
        """Check Redis connectivity."""
        try:
            import redis
            from django.conf import settings

            # Try to connect using Celery broker URL
            import os
            broker_url = os.getenv('CELERY_BROKER_URL', '')

            if broker_url.startswith('redis://'):
                from urllib.parse import urlparse
                parsed = urlparse(broker_url)
                r = redis.Redis(host=parsed.hostname, port=parsed.port)
                r.ping()
                return {'status': 'healthy', 'message': 'Redis connection OK'}
            else:
                return {'status': 'warning', 'message': 'Redis URL not configured'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def check_configurations(self):
        """Check system configurations."""
        try:
            config_count = Settings.objects.filter(is_active=True).count()
            user_count = User.objects.filter(
                settings__key='email_config',
                settings__is_active=True
            ).distinct().count()

            return {
                'status': 'healthy',
                'active_configs': config_count,
                'configured_users': user_count
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def print_status_summary(self, status_data, user):
        """Print formatted status summary."""
        scope = f"for user {user.username}" if user else "system-wide"
        self.stdout.write(f"\n📊 Status Summary ({scope}):")

        # Users
        self.stdout.write(f"\n👥 Users:")
        self.stdout.write(f"   Total: {status_data['users']['total']}")
        self.stdout.write(f"   With email config: {status_data['users']['with_email_config']}")

        # Emails
        self.stdout.write(f"\n📧 Emails:")
        self.stdout.write(f"   Total: {status_data['emails']['total']}")
        for status, count in status_data['emails'].items():
            if status != 'total':
                self.stdout.write(f"   {status}: {count}")

        # Attachments
        self.stdout.write(f"\n📎 Attachments:")
        self.stdout.write(f"   Total: {status_data['attachments']['total']}")
        self.stdout.write(f"   Images: {status_data['attachments']['images']}")

        # JIRA
        self.stdout.write(f"\n🎫 JIRA Issues:")
        self.stdout.write(f"   Total: {status_data['jira_issues']['total']}")

    def output_results(self):
        """Output final results."""
        if self.options['json']:
            self.stdout.write(json.dumps(self.results, indent=2))
        elif not self.options['quiet']:
            if self.results['success']:
                self.log_success("✅ Test completed successfully")
            else:
                self.log_error("❌ Test failed")
                for error in self.results['errors']:
                    self.log_error(f"   Error: {error}")
