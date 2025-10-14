"""
Django management command to initialize threadline settings configuration
"""
import json
import logging
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.conf import settings

from threadline.models import Settings
from threadline.utils.prompt_config_manager import PromptConfigManager


class Command(BaseCommand):
    """
    Initialize threadline settings configuration for specified user
    """
    help = 'Initialize threadline settings configuration for a user'

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
            '--language',
            type=str,
            default=settings.DEFAULT_LANGUAGE,
            help=f"Language for prompt configuration "
                 f"(default: {settings.DEFAULT_LANGUAGE})"
        )
        parser.add_argument(
            '--scene',
            type=str,
            default=settings.DEFAULT_SCENE,
            help=f"Scene for prompt configuration "
                 f"(default: {settings.DEFAULT_SCENE})"
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

        language = options['language']
        scene = options['scene']
        force_update = options['force']

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.logger.error(
                f'User "{username}" does not exist. '
                f'Please create the user first.'
            )
            return

        # Initialize PromptConfigManager and generate user config
        try:
            config_manager = PromptConfigManager()
            user_prompt_config = config_manager.generate_user_config(
                language, scene
            )
            self.logger.info(
                f'Generated prompt config for language: {language}, '
                f'scene: {scene}'
            )
        except Exception as e:
            self.logger.error(
                f'Failed to load prompt configuration: {e}'
            )
            return

        # Threadline settings configuration with unified email_config
        threadline_settings = {
            'email_config': {
                # Default to 'auto_assign' for simplified multi-user setup
                # Change to 'custom_imap' if users need individual IMAP config
                'mode': 'auto_assign',
                'imap_config': {
                    'imap_host': 'your-imap-server-hostname',
                    'smtp_ssl_port': 465,
                    'smtp_starttls_port': 587,
                    'imap_ssl_port': 993,
                    'username': 'your-email-username',
                    'password': 'your-email-password',
                    'use_ssl': True,
                    'use_starttls': False,
                    'delete_after_fetch': False
                },
                'filter_config': {
                    'filters': [],
                    'exclude_patterns': [
                        'spam',
                        'newsletter'
                    ],
                    'max_age_days': 7
                }
            },
            'issue_config': {
                'enable': False,
                'engine': 'jira',
                'jira': {
                    'url': 'your-jira-url',
                    'username': 'your-jira-username',
                    'api_token': 'your-api-token-or-password',
                    'summary_prefix': '[AI]',
                    'summary_timestamp': True,
                    'project_key': 'your-default-project-key',
                    'allow_project_keys': ['PRJ', 'REQ'],
                    'project_prompt': (
                        'The project key is: your-default-project-key, only'
                        'Only return the project key, do not add any '
                        'other text.'
                        'leave empty if you want to use default project key'
                    ),
                    'default_issue_type': 'your-default-issue-type',
                    'default_priority': 'your-default-priority',
                    'epic_link': 'your-epic-link-key',
                    'assignee': 'your-default-assignee-username',
                    'allow_assignees': ['assignee1', 'assignee2'],
                    'description_prompt': (
                        'Convert the provided content into Jira Markup Wiki '
                        'format, fully preserving all information and '
                        'ensuring '
                        'clear structure and hierarchy. When appropriate, use '
                        'Jira Wiki syntax elements such as headings, lists, '
                        'tables, blockquotes, and code blocks for formatting. '
                        'Do not omit any information, do not add extra '
                        'explanations or unrelated content, and output only '
                        'the converted Jira Wiki text.'
                    ),
                    'assignee_prompt': (
                        'Assign the issue to the following user: '
                        'your-default-assignee-username'
                        'Only return the username, do not add any other text. '
                        'leave empty if you want to use default assignee'
                    )
                }
            },
            'prompt_config': user_prompt_config,
            'webhook_config': {
                'url': '',
                'events': [
                    'failed', 'completed'
                ],
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

        for key, value in threadline_settings.items():
            setting, created = Settings.objects.get_or_create(
                user=user,
                key=key,
                defaults={
                    'value': value,
                    'description': f'Threadline {key} configuration',
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
                    setting.description = f'Threadline {key} configuration'
                    setting.is_active = True
                    setting.save()
                    updated_count += 1
                    self.logger.warning(f'✓ Updated setting: {key}')
                else:
                    skipped_count += 1
                    self.logger.warning(
                        f'⚠ Skipped existing setting: {key} '
                        f'(use --force to update)'
                    )

        # Summary
        self.logger.info(
            f'\n🎉 Threadline settings initialization completed for '
            f'user "{username}"!\n'
            f'Created: {created_count} settings\n'
            f'Updated: {updated_count} settings\n'
            f'Skipped: {skipped_count} settings\n'
            f'Total: {created_count + updated_count + skipped_count} settings'
        )

        if created_count > 0 or updated_count > 0:
            self.logger.info(
                f'\n📝 Next steps:\n'
                f'1. Visit Django Admin: '
                f'http://localhost:8000/admin/v1/threadline/settings/\n'
                f'2. Update the following configurations:\n'
                f'   • email_config - Your email server details\n'
                f'   • issue_config - Your issue creation settings\n'
                f'   • prompt_config - Customize AI prompts if needed\n'
                f'   • webhook_config - Configure external notifications '
                f'(optional)\n'
                f'3. Configure periodic tasks in Django Admin:\n'
                f'   • schedule_email_fetch\n'
                f'   • reset_stuck_processing_email\n'
                f'4. Test webhook configuration:\n'
                f'   • python manage.py test_webhook'
            )

    def list_settings(self):
        """List all available settings keys"""
        self.logger.info('Available threadline settings keys:')

        settings_info = [
            ('email_config',
             'Unified email configuration including IMAP settings, '
             'mode selection, and filtering rules'),
            ('issue_config',
             'Issue creation engine configuration (JIRA, email, Slack, etc.)'),
            ('prompt_config',
             'AI prompt templates for email/attachment/summary processing'),
            ('webhook_config',
             'Webhook configuration for external notifications')
        ]

        for key, description in settings_info:
            self.logger.info(f'  • {key}: {description}')

        self.logger.info(
            f'\nUsage examples:\n'
            f'  python manage.py init_threadline_settings --user admin\n'
            f'  python manage.py init_threadline_settings --user admin '
            f'--language zh-CN --scene product_issue\n'
            f'  python manage.py init_threadline_settings --user admin '
            f'--force\n'
            f'  python manage.py init_threadline_settings --list'
        )