"""
Django management command to initialize threadline settings configuration
"""
import json
import logging
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.conf import settings

from threadline.models import Settings


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

        # Threadline settings configuration
        threadline_settings = {
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
                        'Only return the project key, do not add any other text.'
                        'leave empty if you want to use default project key'
                    ),
                    'default_issue_type': 'your-default-issue-type',
                    'default_priority': 'your-default-priority',
                    'epic_link': 'your-epic-link-key',
                    'assignee': 'your-default-assignee-username',
                    'allow_assignees': ['assignee1', 'assignee2'],
                    'description_prompt': (
                        'Convert the provided content into Jira Markup Wiki '
                        'format, fully preserving all information and ensuring '
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
            'prompt_config': {
                'output_language': settings.LLM_OUTPUT_LANGUAGE,
                'email_content_prompt': (
                    (
                        'Organize the provided email content (which may include '
                        'chat records or message bodies) in chronological order '
                        'into a conversation text with minimal polishing (clearly '
                        'mark any assumptions), without altering any original '
                        'meaning and retaining all information. Output format: '
                        '[Date Time] Speaker: Content (on a single line, or '
                        'wrapped across multiple lines if necessary), with image '
                        'placeholders [IMAGE: filename.png] placed on separate '
                        'lines in their original positions. Date and time: if '
                        'the date is unknown, display only the time; if known, '
                        'display both date and time. Conversation text must be '
                        'plain text (excluding emojis, special characters, etc.) '
                        'with clear structure. Always preserve the original '
                        'language of the conversation; if the specified output '
                        'language differs from the original language, include '
                        'the original text on top and the translated text below. '
                        'No explanations or additional content should be provided.'
                    )
                ),
                'ocr_prompt': (
                    'Organize the provided OCR results into plain text output, '
                    'using Markdown formatting when necessary for code or quoted '
                    'content (e.g., ``` for code blocks, > for quotes). Describe '
                    'all explanatory or interpretive content in the specified '
                    'output language, while keeping all actual OCR text in the '
                    'original language from the image. Fully retain and describe '
                    'all content without omission. Clearly highlight any normal, '
                    'abnormal, or valuable information. Attempt to correct and '
                    'standardize incomplete, unclear, or potentially erroneous '
                    'OCR content without altering its original meaning, and mark '
                    'any uncertain parts as [unclear]. Produce only structured '
                    'text with necessary Markdown formatting, without any '
                    'additional explanations, summaries, or unrelated content.'
                ),
                'summary_prompt': (
                    'Based on the provided content (including chronological chat '
                    'records and OCR-recognized content from images), organize the '
                    'chat records in chronological order, preserving the original '
                    'speaker and language for each entry, fully retaining all '
                    'information, and using Markdown formatting when necessary for '
                    'code or quoted content. The output should include four sections: '
                    '1) **Main Content**: list the key points of the current '
                    'conversation; 2) **Process Description**: provide a detailed '
                    'description of the problem and its reproduction steps, marking '
                    'any uncertain information as "unknown"; 3) **Solution** (if '
                    'unresolved, indicate attempted measures): if the issue is '
                    'resolved, list the solution; if unresolved, list measures '
                    'already taken and their results, optionally including possible '
                    'causes clearly marked as (speculation); 4) **Resolution Status**: '
                    'indicate whether the issue has been resolved (Yes/No). Output '
                    'must be well-structured, hierarchically clear plain text, '
                    'without any additional explanations, summaries, or extra content, '
                    'while highlighting any normal, abnormal, or valuable information '
                    'for quick reference.'
                ),
                'summary_title_prompt': (
                    'Based on the chat records, extract a single structured '
                    'title in the format: [Issue Category][Participant]Title '
                    'Content; the title should use a verb-object structure, '
                    'be concise, and accurately express the core problem or '
                    'requirement, avoiding vague terms, with a maximum length '
                    'of 300 characters; if the information is unclear, add '
                    '[To Be Confirmed]; if multiple issues exist, extract '
                    'only the most critical and central one, generating a '
                    'single structured title.'
                )
            },
            'webhook_config': {
                'url': '',
                'events': ['issue_success', 'ocr_failed', 'llm_summary_failed'],
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
                        f'⚠ Skipped existing setting: {key} (use --force to update)'
                    )

        # Summary
        self.logger.info(
            f'\n🎉 Threadline settings initialization completed for user "{username}"!\n'
            f'Created: {created_count} settings\n'
            f'Updated: {updated_count} settings\n'
            f'Skipped: {skipped_count} settings\n'
            f'Total: {created_count + updated_count + skipped_count} settings'
        )

        if created_count > 0 or updated_count > 0:
            self.logger.info(
                f'\n📝 Next steps:\n'
                f'1. Visit Django Admin: http://localhost:8000/admin/v1/threadline/settings/\n'
                f'2. Update the following configurations:\n'
                f'   • email_config - Your email server details\n'
                f'   • issue_config - Your issue creation settings\n'
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
        self.logger.info('Available threadline settings keys:')

        settings_info = [
            ('email_config', 'Email server connection and authentication settings'),
            ('email_filter_config', 'Email filtering and processing rules'),
            ('issue_config', 'Issue creation engine configuration (JIRA, email, Slack, etc.)'),
            ('prompt_config', 'AI prompt templates for email/attachment/summary processing'),
            ('webhook_config', 'Webhook configuration for external notifications')
        ]

        for key, description in settings_info:
            self.logger.info(f'  • {key}: {description}')

        self.logger.info(
            f'\nUsage examples:\n'
            f'  python manage.py init_threadline_settings --user admin\n'
            f'  python manage.py init_threadline_settings --user admin --force\n'
            f'  python manage.py init_threadline_settings --list'
        )