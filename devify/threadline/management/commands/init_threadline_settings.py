"""
Django management command to initialize threadline settings configuration.

This command initializes threadline settings for a specified user, including:
- email_config: Email collection configuration
- issue_config: Issue creation configuration (loaded from YAML)
- prompt_config: AI prompt templates
"""

import logging
import os

import yaml
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from threadline.models import Settings
from threadline.utils.issues.issue_factory import normalize_issue_engine
from threadline.utils.prompt_config_manager import PromptConfigManager

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Management command to initialize threadline settings for users.

    This command creates all required settings configurations for a user,
    loading issue configuration from YAML file in conf/threadline/issues/.
    """

    help = "Initialize threadline settings configuration for a user"

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
        Load issue configuration from YAML files.

        Returns:
            dict: Issue configuration dictionary merged from the common
                base config plus the engine-specific config.

        Raises:
            FileNotFoundError: If config file not found
            ValueError: If config file is invalid YAML
        """
        base_dir = os.path.dirname(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
        )

        config_dir = os.path.join(base_dir, "conf", "threadline", "issues")
        common_config_file = os.path.join(config_dir, "issue_config.yaml")
        if not os.path.exists(common_config_file):
            self.logger.error(
                f"Issue config file not found in: {common_config_file}\n"
                f"Please ensure the configuration file exists."
            )
            raise FileNotFoundError(
                f"Issue configuration file not found in: {common_config_file}"
            )

        try:
            common_config = self._load_yaml_config(common_config_file)
            engine_name = normalize_issue_engine(
                common_config.get("issue_engine", "jira")
            )
            engine_config_file = self._get_issue_engine_config_file(
                config_dir,
                engine_name,
            )
            engine_config = (
                self._load_yaml_config(engine_config_file)
                if engine_config_file
                else {}
            )

            config = self._deep_merge_dicts(common_config, engine_config)
            config["issue_engine"] = engine_name
            self.logger.info(
                f"Loaded issue configuration from: {common_config_file} + "
                f"{engine_config_file or '<none>'}"
            )
            return config

        except yaml.YAMLError as e:
            self.logger.error(f"Invalid YAML in issue config file: {e}")
            raise ValueError(f"Invalid YAML configuration: {e}")

    def _load_yaml_config(self, file_path):
        """
        Load a YAML config file from disk.

        Args:
            file_path: Absolute config file path.

        Returns:
            dict: Parsed YAML dictionary or an empty dict when the file has
                no content.
        """
        with open(file_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        return config or {}

    def _get_issue_engine_config_file(self, config_dir, engine_name):
        """
        Return the engine-specific config file path if it exists.
        """
        engine_config_files = {
            "jira": "jira_config.yaml",
            "feishu_bitable": "feishu_bitable_config.yaml",
        }
        file_name = engine_config_files.get(engine_name)
        if not file_name:
            return None

        config_file = os.path.join(config_dir, file_name)
        return config_file if os.path.exists(config_file) else None

    def _deep_merge_dicts(self, base, override):
        """
        Deep-merge two configuration dictionaries.

        Nested dictionaries are merged recursively. Scalar values in the
        override config replace the base values.
        """
        merged = dict(base or {})
        for key, value in (override or {}).items():
            existing = merged.get(key)
            if isinstance(existing, dict) and isinstance(value, dict):
                merged[key] = self._deep_merge_dicts(existing, value)
            else:
                merged[key] = value
        return merged

    def add_arguments(self, parser):
        """
        Add command line arguments.

        Args:
            parser: ArgumentParser instance to add arguments to
        """
        parser.add_argument(
            "--user", type=str, help="Username to initialize settings for"
        )
        parser.add_argument(
            "--language",
            type=str,
            default=settings.DEFAULT_LANGUAGE,
            help=(
                f"Language for prompt configuration "
                f"(default: {settings.DEFAULT_LANGUAGE})"
            ),
        )
        parser.add_argument(
            "--scene",
            type=str,
            default=settings.DEFAULT_SCENE,
            help=(
                f"Scene for prompt configuration "
                f"(default: {settings.DEFAULT_SCENE})"
            ),
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force update existing settings",
        )
        parser.add_argument(
            "--list",
            action="store_true",
            help="List all available settings keys",
        )

    def handle(self, *args, **options):
        """
        Execute the management command.

        Args:
            *args: Variable length argument list
            **options: Arbitrary keyword arguments from command line
        """
        if options["list"]:
            self.list_settings()
            return

        username = options["user"]
        if not username:
            self.logger.error(
                "--user argument is required unless --list is used."
            )
            return

        language = options["language"]
        scene = options["scene"]
        force_update = options["force"]

        user = self._get_user(username)
        if not user:
            return

        user_prompt_config = self._load_prompt_config(language, scene)
        if not user_prompt_config:
            return

        issue_config = self._load_issue_config()

        threadline_settings = self._build_settings_dict(
            user_prompt_config, issue_config
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
                f"Please create the user first."
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
                f"Generated prompt config for language: {language}, "
                f"scene: {scene}"
            )
            return user_prompt_config
        except Exception as e:
            self.logger.error(f"Failed to load prompt configuration: {e}")
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
                f"Failed to load issue configuration: {e}\n"
                f"Skipping issue_config initialization."
            )
            return {
                "enable": False,
                "issue_engine": "jira",
                "jira": {},
                "feishu_bitable": {},
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
            "email_config": self._get_email_config(),
            "issue_config": issue_config,
            "prompt_config": user_prompt_config,
        }

    def _get_email_config(self):
        """
        Get default email configuration.

        Returns:
            dict: Email configuration
        """
        return {
            "mode": "auto_assign",
            "imap_config": {
                "imap_host": "your-imap-server-hostname",
                "smtp_ssl_port": 465,
                "smtp_starttls_port": 587,
                "imap_ssl_port": 993,
                "username": "your-email-username",
                "password": "your-email-password",
                "use_ssl": True,
                "use_starttls": False,
                "delete_after_fetch": False,
            },
            "filter_config": {
                "filters": [],
                "exclude_patterns": ["spam", "newsletter"],
                "max_age_days": 7,
            },
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
                    "value": value,
                    "description": f"Threadline {key} configuration",
                    "is_active": True,
                },
            )

            if created:
                created_count += 1
                self.logger.info(f"✓ Created setting: {key}")
            else:
                if force_update:
                    setting.value = value
                    setting.description = f"Threadline {key} configuration"
                    setting.is_active = True
                    setting.save()
                    updated_count += 1
                    self.logger.warning(f"✓ Updated setting: {key}")
                else:
                    skipped_count += 1
                    self.logger.warning(
                        f"⚠ Skipped existing setting: {key} "
                        f"(use --force to update)"
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
            f"\n🎉 Threadline settings initialization completed!\n"
            f"Created: {created_count} settings\n"
            f"Updated: {updated_count} settings\n"
            f"Skipped: {skipped_count} settings\n"
            f"Total: {total} settings"
        )

    def _log_next_steps(self):
        """Log next steps for user configuration."""
        self.logger.info(
            f"\n📝 Next steps:\n"
            f"1. Visit Django Admin: "
            f"http://localhost:8000/admin/v1/threadline/settings/\n"
            f"2. Update the following configurations:\n"
            f"   • email_config - Your email server details\n"
            f"   • issue_config - Your issue creation settings "
            f"(JIRA / Feishu Bitable)\n"
            f"   • prompt_config - Customize AI prompts if needed\n"
            f"   • notification channel - Configure in "
            f"admin/threadline/config/\n"
            f"3. Configure periodic tasks in Django Admin:\n"
            f"   • schedule_email_fetch\n"
            f"   • reset_stuck_processing_email\n"
            f"4. Test the configured notification channel:\n"
            f"   • python manage.py test_webhook"
        )

    def list_settings(self):
        """
        List all available settings keys and their descriptions.
        """
        self.logger.info("Available threadline settings keys:")

        settings_info = [
            (
                "email_config",
                "Required - Unified email configuration including IMAP "
                "settings, mode selection, and filtering rules",
            ),
            (
                "issue_config",
                "Optional - Issue creation configuration for JIRA or "
                "Feishu Bitable. Only needed if you want to create "
                "records automatically from emails.",
            ),
            (
                "prompt_config",
                "Required - AI prompt templates for email/attachment/summary "
                "processing",
            ),
        ]

        for key, description in settings_info:
            self.logger.info(f"  • {key}: {description}")

        self.logger.info(
            f"\nUsage examples:\n"
            f"  python manage.py init_threadline_settings --user admin\n"
            f"  python manage.py init_threadline_settings --user admin "
            f"--language zh-CN --scene product_issue\n"
            f"  python manage.py init_threadline_settings --user admin "
            f"--force\n"
            f"  python manage.py init_threadline_settings --list"
        )
