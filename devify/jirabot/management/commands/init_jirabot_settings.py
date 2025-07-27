"""
Django management command to initialize jirabot settings configuration
"""
import json
import logging
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from jirabot.models import Settings


class Command(BaseCommand):
    """
    Initialize jirabot settings configuration for specified user
    """
    help = 'Initialize jirabot settings configuration for a user'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            help="Username to initialize settings for"
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update existing settings'
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='List all available settings keys'
        )

    def handle(self, *args, **options):
        if options['list']:
            self.list_settings()
            return

        username = options['user']
        if not username:
            self.logger.error(
                '--user argument is required unless --list is used.'
            )
            return

        force_update = options['force']

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.logger.error(
                f'User "{username}" does not exist. Please create the user first.'
            )
            return

        # Jirabot settings configuration
        jirabot_settings = {
            'email_config': {
                'imap_host': 'your-imap-server-hostname',
                'smtp_ssl_port': 465,
                'smtp_starttls_port': 587,
                'imap_ssl_port': 993,
                'username': 'your-email-username',
                'password': 'your-email-password',
                'use_ssl': True,
                'use_starttls': False
            },
            'email_filter_config': {
                'filters': [],
                'exclude_patterns': [
                    'spam',
                    'newsletter'
                ],
                'max_age_days': 7
            },
            'jira_config': {
                'username': 'your-jira-username',
                'api_token': 'your-api-token-or-password',
                'project_key': 'your-project-key',
                'default_issue_type': 'your-default-issue-type',
                'default_priority': 'your-default-priority',
                'epic_link': 'your-epic-link-key',
                'assignee': 'your-assignee-username'
            },
            'prompt_config': {
                'email_content_prompt': (
                    'Organize the following email content in chronological order. '
                    'Format messages and images for further processing. '
                    'Extract key information and maintain context.'
                ),
                'ocr_prompt': (
                    'Process the following OCR text from images. '
                    'Extract key information and summarize relevant context and issues. '
                    'Focus on actionable items and technical details.'
                ),
                'summary_prompt': (
                    'Summarize the following email content for task creation. '
                    'Include main issues, analysis, and action items. '
                    'If OCR content is present, incorporate relevant information. '
                    'Organize the summary for clarity and actionable steps.'
                ),
                'summary_title_prompt': (
                    'Summarize the main issue or requirement from the following '
                    'information and generate a clear, concise title in native language. '
                    'Focus on the core need or problem, using a brief verb-object '
                    'structure. Avoid product-specific or platform-specific terms.'
                )
            },
            'webhook_config': {
                'url': '',
                'events': ['jira_success', 'ocr_failed', 'summary_failed'],
                'timeout': 10,
                'retries': 3,
                'headers': {},
                'language': 'zh-hans',
                'provider': 'feishu'
            }
        }

        # Initialize settings
        created_count = 0
        updated_count = 0
        skipped_count = 0

        for key, value in jirabot_settings.items():
            setting, created = Settings.objects.get_or_create(
                user=user,
                key=key,
                defaults={
                    'value': value,
                    'description': f'Jirabot {key} configuration',
                    'is_active': True
                }
            )

            if created:
                created_count += 1
                self.logger.info(f'✓ Created setting: {key}')
            else:
                if force_update:
                    # Update existing setting
                    setting.value = value
                    setting.description = f'Jirabot {key} configuration'
                    setting.is_active = True
                    setting.save()
                    updated_count += 1
                    self.logger.warning(f'✓ Updated setting: {key}')
                else:
                    skipped_count += 1
                    self.logger.warning(
                        f'⚠ Skipped existing setting: {key} (use --force to update)'
                    )

        # Summary
        self.logger.info(
            f'\n🎉 Jirabot settings initialization completed for user "{username}"!\n'
            f'Created: {created_count} settings\n'
            f'Updated: {updated_count} settings\n'
            f'Skipped: {skipped_count} settings\n'
            f'Total: {created_count + updated_count + skipped_count} settings'
        )

        if created_count > 0 or updated_count > 0:
            self.logger.info(
                f'\n📝 Next steps:\n'
                f'1. Visit Django Admin: http://localhost:8000/admin/v1/jirabot/settings/\n'
                f'2. Update the following configurations:\n'
                f'   • email_config - Your email server details\n'
                f'   • jira_config - Your JIRA server details\n'
                f'   • prompt_config - Customize AI prompts if needed\n'
                f'   • webhook_config - Configure external notifications (optional)\n'
                f'3. Configure periodic tasks in Django Admin:\n'
                f'   • schedule_email_processing_tasks\n'
                f'   • reset_stuck_processing_email\n'
                f'4. Test webhook configuration:\n'
                f'   • python manage.py test_webhook'
            )

    def list_settings(self):
        """List all available settings keys"""
        self.logger.info('Available jirabot settings keys:')

        settings_info = [
            ('email_config', 'Email server connection and authentication settings'),
            ('email_filter_config', 'Email filtering and processing rules'),
            ('jira_config', 'JIRA integration and default issue creation settings'),
            ('prompt_config', 'AI prompt templates for email/attachment/summary processing'),
            ('webhook_config', 'Webhook configuration for external notifications')
        ]

        for key, description in settings_info:
            self.logger.info(f'  • {key}: {description}')

        self.logger.info(
            f'\nUsage examples:\n'
            f'  python manage.py init_jirabot_settings --user admin\n'
            f'  python manage.py init_jirabot_settings --user admin --force\n'
            f'  python manage.py init_jirabot_settings --list'
        )