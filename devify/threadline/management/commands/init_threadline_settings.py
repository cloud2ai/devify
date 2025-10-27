"""
Django management command to initialize threadline settings configuration.

This command initializes threadline settings for a specified user, including:
- email_config: Email collection configuration
- issue_config: JIRA issue creation configuration (loaded from YAML)
- prompt_config: AI prompt templates
- webhook_config: Webhook notification settings
"""
import logging
import os

import yaml
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from threadline.models import Settings
from threadline.utils.prompt_config_manager import PromptConfigManager

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Management command to initialize threadline settings for users.

    This command creates all required settings configurations for a user,
    loading JIRA configuration from YAML file in conf/threadline/issues/.
    """

    help = 'Initialize threadline settings configuration for a user'

    def __init__(self, *args, **kwargs):
        """
        Initialize the command and set up logger.

        Args:
            *args: Variable length argument list
            **kwargs: Arbitrary keyword arguments
        """
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(__name__)

    def load_issue_config(self):
        """
        Load issue configuration from YAML file.

        Returns:
            dict: Issue configuration dictionary

        Raises:
            FileNotFoundError: If config file not found
            ValueError: If config file is invalid YAML
        """
        base_dir = os.path.dirname(
            os.path.dirname(
                os.path.dirname(
                    os.path.dirname(os.path.abspath(__file__))
                )
            )
        )

        config_file = os.path.join(
            base_dir,
            'conf',
            'threadline',
            'issues',
            'jira_config.yaml'
        )

        if not os.path.exists(config_file):
            self.logger.error(
                f'Issue config file not found: {config_file}\n'
                f'Please ensure the configuration file exists.'
            )
            raise FileNotFoundError(
                f'JIRA configuration file not found: {config_file}'
            )

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            self.logger.info(
                f'Loaded JIRA configuration from: {config_file}'
            )
            return config

        except yaml.YAMLError as e:
            self.logger.error(
                f'Invalid YAML in issue config file: {e}'
            )
            raise ValueError(f'Invalid YAML configuration: {e}')

    def add_arguments(self, parser):
        """
        Add command line arguments.

        Args:
            parser: ArgumentParser instance to add arguments to
        """
        parser.add_argument(
            '--user',
            type=str,
            help="Username to initialize settings for"
        )
        parser.add_argument(
            '--language',
            type=str,
            default=settings.DEFAULT_LANGUAGE,
            help=(
                f"Language for prompt configuration "
                f"(default: {settings.DEFAULT_LANGUAGE})"
            )
        )
        parser.add_argument(
            '--scene',
            type=str,
            default=settings.DEFAULT_SCENE,
            help=(
                f"Scene for prompt configuration "
                f"(default: {settings.DEFAULT_SCENE})"
            )
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
        """
        Execute the management command.

        Args:
            *args: Variable length argument list
            **options: Arbitrary keyword arguments from command line
        """
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

        user = self._get_user(username)
        if not user:
            return

        user_prompt_config = self._load_prompt_config(language, scene)
        if not user_prompt_config:
            return

        issue_config = self._load_issue_config()

        threadline_settings = self._build_settings_dict(
            user_prompt_config,
            issue_config
        )

        self._initialize_settings(user, threadline_settings, force_update)

    def _get_user(self, username):
        """
        Get user by username.

        Args:
            username: Username to look up

        Returns:
            User instance or None if not found
        """
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            self.logger.error(
                f'User "{username}" does not exist. '
                f'Please create the user first.'
            )
            return None

    def _load_prompt_config(self, language, scene):
        """
        Load prompt configuration.

        Args:
            language: Language code
            scene: Scene identifier

        Returns:
            dict: Prompt configuration or None on error
        """
        try:
            config_manager = PromptConfigManager()
            user_prompt_config = config_manager.generate_user_config(
                language, scene
            )
            self.logger.info(
                f'Generated prompt config for language: {language}, '
                f'scene: {scene}'
            )
            return user_prompt_config
        except Exception as e:
            self.logger.error(f'Failed to load prompt configuration: {e}')
            return None

    def _load_issue_config(self):
        """
        Load issue configuration from YAML file.

        Returns:
            dict: Issue configuration dictionary with fallback values
        """
        try:
            return self.load_issue_config()
        except (FileNotFoundError, ValueError) as e:
            self.logger.error(
                f'Failed to load JIRA configuration: {e}\n'
                f'Skipping issue_config initialization.'
            )
            return {
                'enable': False,
                'issue_engine': 'jira'
            }

    def _build_settings_dict(self, user_prompt_config, issue_config):
        """
        Build settings dictionary with all configurations.

        Args:
            user_prompt_config: Prompt configuration dict
            issue_config: Issue configuration dict

        Returns:
            dict: Complete settings dictionary
        """
        return {
            'email_config': self._get_email_config(),
            'issue_config': issue_config,
            'prompt_config': user_prompt_config,
            'webhook_config': self._get_webhook_config()
        }

    def _get_email_config(self):
        """
        Get default email configuration.

        Returns:
            dict: Email configuration
        """
        return {
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
                'exclude_patterns': ['spam', 'newsletter'],
                'max_age_days': 7
            }
        }

    def _get_webhook_config(self):
        """
        Get default webhook configuration.

        Returns:
            dict: Webhook configuration
        """
        return {
            'url': '',
            'events': ['failed', 'completed'],
            'timeout': 10,
            'retries': 3,
            'headers': {},
            'language': 'zh-hans',
            'provider': 'feishu'
        }

    def _initialize_settings(self, user, threadline_settings, force_update):
        """
        Initialize settings for user.

        Args:
            user: User instance
            threadline_settings: Settings dictionary
            force_update: Whether to force update existing settings
        """
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

        self._log_summary(created_count, updated_count, skipped_count)

        if created_count > 0 or updated_count > 0:
            self._log_next_steps()

    def _log_summary(self, created_count, updated_count, skipped_count):
        """
        Log initialization summary.

        Args:
            created_count: Number of created settings
            updated_count: Number of updated settings
            skipped_count: Number of skipped settings
        """
        total = created_count + updated_count + skipped_count
        self.logger.info(
            f'\n🎉 Threadline settings initialization completed!\n'
            f'Created: {created_count} settings\n'
            f'Updated: {updated_count} settings\n'
            f'Skipped: {skipped_count} settings\n'
            f'Total: {total} settings'
        )

    def _log_next_steps(self):
        """Log next steps for user configuration."""
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
        """
        List all available settings keys and their descriptions.
        """
        self.logger.info('Available threadline settings keys:')

        settings_info = [
            (
                'email_config',
                'Required - Unified email configuration including IMAP '
                'settings, mode selection, and filtering rules'
            ),
            (
                'issue_config',
                'Optional - JIRA issue creation configuration. Only needed '
                'if you want to automatically create JIRA issues from emails.'
            ),
            (
                'prompt_config',
                'Required - AI prompt templates for email/attachment/summary '
                'processing'
            ),
            (
                'webhook_config',
                'Optional - Webhook configuration for external notifications'
            )
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
