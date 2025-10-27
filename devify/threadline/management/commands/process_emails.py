"""
Django management command for unified email processing.

This command combines the functionality of scan_emails.py and
process_file_emails.py, providing a unified interface for processing
emails from various sources based on user configuration.

The command automatically detects the appropriate email source (IMAP or
file system) based on the user's configuration.

Usage:
    # Process emails for all users with email configuration
    python manage.py process_emails

    # Process emails for a specific user (auto-detect source)
    python manage.py process_emails --user username

    # Process a specific email by ID (auto-find user)
    python manage.py process_emails --email-id 123

    # Process a specific email by ID for a specific user
    python manage.py process_emails --user username --email-id 123

    # Force processing even if recent task exists
    python manage.py process_emails --user username --force

    # Force process a specific email by ID
    python manage.py process_emails --email-id 123 --force

    # Enable debug logging
    python manage.py process_emails --user username --debug
"""

import logging
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from threadline.models import Settings, EmailTask, EmailMessage, EmailStatus
from threadline.tasks import scan_user_emails
from threadline.utils.email import EmailProcessor, EmailSource

# Initialize logger for this module
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Unified command for processing emails from various sources.

    This command automatically detects the appropriate email source based on
    user configuration:
    - auto_assign mode: File system processing with email aliases
    - custom_imap mode: IMAP server processing with custom configuration
    - Legacy mode: IMAP configuration without mode specification
    - User-specific configuration
    - Force processing options
    - Debug logging
    """
    help = (
        "Process emails for users from various sources (auto-detected based "
        "on user configuration)"
    )

    def add_arguments(self, parser):
        """
        Add command line arguments for the management command.

        Args:
            parser: ArgumentParser instance to add arguments to
        """
        parser.add_argument(
            "--user",
            type=str,
            help=(
                "Username to process emails for (optional, processes all "
                "users if not specified)"
            ),
        )
        parser.add_argument(
            "--email-id",
            type=int,
            help=(
                "Specific email ID to reprocess (can be used independently)"
            ),
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help=(
                "Force processing even if recent task exists"
            ),
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            help=(
                "Enable debug logging for detailed output"
            ),
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help=(
                "Enable verbose output"
            ),
        )

    def handle(self, *args, **options):
        """
        Handle the command logic for processing emails.

        Args:
            *args: Variable length argument list
            **options: Keyword arguments from command line options
        """
        # Set debug logging level if debug flag is enabled
        if options["debug"]:
            logging.getLogger().setLevel(logging.DEBUG)
            logger.info("Debug logging enabled")

        # Check if specific email ID is provided
        if options["email_id"]:
            self.process_single_email_by_id(
                options["email_id"], options["force"], options["verbose"]
            )
        elif options["user"]:
            try:
                user = User.objects.get(username=options["user"])
                self.process_for_user(
                    user, options["force"], options["verbose"]
                )
            except User.DoesNotExist:
                logger.error(f'User "{options["user"]}" does not exist')
                raise CommandError(f'User "{options["user"]}" does not exist')
        else:
            self.process_for_all_users(
                options["force"], options["verbose"]
            )

    def process_for_user(self, user, force=False, verbose=False):
        """
        Process emails for a specific user.
        Automatically detects the appropriate email source based on
        user configuration.

        Args:
            user: User instance
            force: Whether to force processing even if recent task exists
            verbose: Whether to enable verbose output
        """
        logger.info(f"Processing emails for user: {user.username}")

        # Get user settings
        try:
            email_config = user.settings.get(
                key="email_config", is_active=True
            )
            logger.info(
                f"Found email configuration for user {user.username}"
            )
        except Settings.DoesNotExist as e:
            logger.error(
                f"Missing email configuration for user "
                f"{user.username}: {e}"
            )
            return

        # Auto-detect email source based on configuration
        source = self._detect_email_source(email_config)
        logger.info(
            f"Auto-detected email source for user "
            f"{user.username}: {source.value}"
        )

        # Check for recent task (only for IMAP source)
        if source == EmailSource.IMAP and not force:
            recent_task = self._check_recent_task(user)
            if recent_task:
                logger.warning(
                    f"User {user.username} has recent task "
                    f"(ID: {recent_task.id}), skipping"
                )
                return

        # Process emails based on detected source
        if source == EmailSource.IMAP:
            self._process_imap_emails(user, email_config, force, verbose)
        elif source == EmailSource.FILE:
            self._process_file_emails(user, email_config, verbose)
        else:
            raise CommandError(f"Unsupported email source: {source}")

    def process_single_email_by_id(self, email_id, force=False, verbose=False):
        """
        Process a single email by ID, automatically finding the user.

        This method triggers the complete email processing workflow including:
        - Email parsing and content extraction
        - OCR processing of image attachments
        - LLM processing of content
        - Summary generation
        - JIRA issue creation
        - Database synchronization

        Args:
            email_id: Email ID to process
            force: Whether to force processing
            verbose: Whether to enable verbose output
        """
        logger.info(f"Processing single email ID={email_id} with complete workflow")

        try:
            # Get the email message (this will automatically get the user)
            email = EmailMessage.objects.get(id=email_id)
            user = email.user
            logger.info(f"Found email ID={email_id} for user: {user.username}")
        except EmailMessage.DoesNotExist:
            raise CommandError(f"Email ID {email_id} not found")

        try:
            # Execute the complete email processing workflow
            from threadline.agents.workflow import execute_email_processing_workflow
            logger.info(f"Starting complete workflow for email ID={email_id}: {email.subject}")
            result = execute_email_processing_workflow(email, force=force)

            if result and result.get('success', False):
                logger.info(f"Successfully completed workflow for email ID={email_id}")
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ Successfully processed email ID={email_id}: {email.subject}"
                    )
                )

                # Show additional info if verbose
                workflow_result = result.get('result', {})
                if verbose:
                    # Show summary info
                    summary_title = workflow_result.get('summary_title')
                    if summary_title:
                        self.stdout.write(
                            f"   📝 Summary: {summary_title[:50]}..."
                        )

                    # Show JIRA issue info
                    issue_result = workflow_result.get('issue_result_data', {})
                    if issue_result:
                        issue_key = issue_result.get('external_id')
                        issue_url = issue_result.get('issue_url')
                        if issue_key:
                            self.stdout.write(
                                f"   📋 JIRA Issue: {issue_key}"
                            )
                        if issue_url:
                            self.stdout.write(
                                f"   🔗 JIRA URL: {issue_url}"
                            )

                        # Show attachment info
                        metadata = issue_result.get('metadata', {})
                        upload_result = metadata.get('upload_result', {})
                        uploaded_count = upload_result.get('uploaded_count', 0)
                        if uploaded_count > 0:
                            self.stdout.write(
                                f"   📎 Attachments: {uploaded_count} uploaded to JIRA"
                            )

                        # Show JIRA field processing details
                        self.stdout.write('   🔧 JIRA Field Processing:')
                        jira_metadata = issue_result.get('metadata', {})
                        if 'project' in jira_metadata:
                            self.stdout.write(f'      Project: {jira_metadata["project"]}')
                        if 'assignee' in issue_result:
                            self.stdout.write(f'      Assignee: {issue_result["assignee"]}')
                        if 'priority' in issue_result:
                            self.stdout.write(f'      Priority: {issue_result["priority"]}')

                        # Show LLM processing details
                        self.stdout.write('   🤖 LLM Processing Details:')
                        self.stdout.write('      - Field assignment completed')
                        self.stdout.write('      - Description converted to JIRA Wiki format')
                        self.stdout.write('      - Attachments processed and uploaded')
            else:
                logger.warning(f"Workflow completed with issues for email ID={email_id}")
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠️ Workflow completed with issues for email ID={email_id}: {email.subject}"
                    )
                )

        except Exception as e:
            logger.error(
                f"Failed to process email ID={email_id}: {e}",
                exc_info=True
            )
            self.stdout.write(
                self.style.ERROR(
                    f"❌ Failed to process email ID={email_id}: {e}"
                )
            )
            raise CommandError(f"Failed to process email ID={email_id}: {e}")

    def process_single_email(self, user, email_id, force=False, verbose=False):
        """
        Process a single email by ID for a specific user.

        Args:
            user: User instance
            email_id: Email ID to process
            force: Whether to force processing
            verbose: Whether to enable verbose output
        """
        logger.info(f'Processing single email ID={email_id} for user: {user.username}')

        try:
            # Get the email message
            email = EmailMessage.objects.get(id=email_id, user=user)
        except EmailMessage.DoesNotExist:
            raise CommandError(
                f'Email ID {email_id} not found for user {user.username}'
            )

        # Get user settings
        try:
            email_config = user.settings.get(
                key="email_config", is_active=True
            )
            logger.info(
                f"Found email configuration for user {user.username}"
            )
        except Settings.DoesNotExist as e:
            logger.error(
                f"Missing email configuration for user "
                f"{user.username}: {e}"
            )
            raise CommandError(
                f'Missing email configuration for user {user.username}'
            )

        # Create EmailProcessor instance
        processor = EmailProcessor(email_config)

        try:
            # Process the single email
            logger.info(f'Reprocessing email ID={email_id}: {email.subject}')
            result = processor.process_single_email(email, force=force)

            if result:
                logger.info(f'Successfully processed email ID={email_id}')
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ Successfully processed email ID={email_id}: {email.subject}"
                    )
                )
            else:
                logger.info(f'Skipped email ID={email_id}: {email.subject}')
                self.stdout.write(
                    self.style.WARNING(
                        f'⚠️ Skipped email ID={email_id}: {email.subject}'
                    )
                )

        except Exception as e:
            logger.error(
                f"Failed to process email ID={email_id}: {e}",
                exc_info=True
            )
            self.stdout.write(
                self.style.ERROR(
                    f"❌ Failed to process email ID={email_id}: {e}"
                )
            )
            raise CommandError(f"Failed to process email ID={email_id}: {e}")

    def process_for_all_users(self, force=False, verbose=False):
        """
        Process emails for all users with email configuration.
        Each user's email source is auto-detected based on their configuration.

        Args:
            force: Whether to force processing even if recent task exists
            verbose: Whether to enable verbose output
        """
        users_with_settings = User.objects.filter(
            settings__key="email_config",
            settings__is_active=True
        ).distinct()

        if not users_with_settings.exists():
            logger.warning('No users with active email settings found')
            return

        logger.info(
            f'Found {users_with_settings.count()} users with email settings'
        )

        for user in users_with_settings:
            try:
                self.process_for_user(user, force, verbose)
            except Exception as e:
                logger.error(
                    f'Failed to process emails for user {user.username}: {e}'
                )

    def _detect_email_source(self, email_config):
        """
        Auto-detect email source based on user configuration.

        Args:
            email_config: User's email configuration dictionary

        Returns:
            EmailSource enum (IMAP or FILE)
        """
        # Check email mode first
        mode = email_config.get('mode', 'custom_imap')

        if mode == 'auto_assign':
            # Auto-assign mode uses file system processing
            logger.info(
                'Detected auto_assign mode, using file system processing'
            )
            return EmailSource.FILE

        elif mode == 'custom_imap':
            # Custom IMAP mode uses IMAP server processing
            imap_config = email_config.get('imap_config', {})
            if ((imap_config.get('imap_host') or imap_config.get('host')) and
                    imap_config.get('username')):
                logger.info(
                    'Detected custom_imap mode with valid IMAP config'
                )
                return EmailSource.IMAP
            else:
                logger.warning(
                    'custom_imap mode detected but IMAP config is incomplete'
                )
                return EmailSource.IMAP  # Still try IMAP as fallback

        # Legacy detection for backward compatibility
        # Check for explicit IMAP configuration (without mode)
        if ('imap_config' in email_config and
                email_config['imap_config']):
            imap_config = email_config['imap_config']
            if ((imap_config.get('host') or imap_config.get('imap_host')) and
                    imap_config.get('username')):
                logger.info('Detected IMAP configuration (legacy mode)')
                return EmailSource.IMAP

        # Default to IMAP if no clear configuration found
        logger.warning('No clear email source configuration found, '
                       'defaulting to IMAP')
        return EmailSource.IMAP

    def _check_recent_task(self, user):
        """
        Check if user has a recent running task.

        Args:
            user: User instance

        Returns:
            EmailTask instance if recent task exists, None otherwise
        """
        return (
            EmailTask.objects.filter(
                user=user,
                status__in=[
                    EmailTask.TaskStatus.PENDING,
                    EmailTask.TaskStatus.RUNNING
                ],
                created_at__gte=(
                    timezone.now() - timedelta(minutes=5)
                )
            ).first()
        )

    def _process_imap_emails(self, user, email_config, force, verbose):
        """
        Process emails from IMAP server for a user.

        Args:
            user: User instance
            email_config: User's email configuration
            force: Whether to force processing
            verbose: Whether to enable verbose output
        """
        try:
            if verbose:
                self.stdout.write(
                    f'Processing IMAP emails for user: {user.username}'
                )

            # Execute IMAP email scanning task
            scan_user_emails.run(user.id)
            logger.info(
                f'Successfully processed IMAP emails for user {user.username}'
            )

            if verbose:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully processed IMAP emails for {user.username}'
                    )
                )
        except Exception as e:
            logger.error(
                f'Failed to process IMAP emails for user {user.username}: {e}'
            )
            if verbose:
                self.stdout.write(
                    self.style.ERROR(
                        f'Failed to process IMAP emails for {user.username}: {e}'
                    )
                )

    def _process_file_emails(self, user, email_config, verbose):
        """
        Process emails from file system for a user.

        Args:
            user: User instance
            email_config: User's email configuration
            verbose: Whether to enable verbose output
        """
        try:
            if verbose:
                self.stdout.write(
                    f'Processing file emails for user: {user.username}'
                )

            # Initialize EmailProcessor with file source for auto_assign mode
            # auto_assign mode uses default file system configuration
            processor = EmailProcessor(
                source=EmailSource.FILE,
                parser_type='flanker',
                email_config=email_config
            )

            # Process emails using the unified processor
            processed_count = 0
            for parsed_email in processor.process_emails():
                processed_count += 1
                if verbose:
                    subject = parsed_email.get('subject', 'No Subject')
                    self.stdout.write(f"Processed email: {subject}")

            logger.info(
                f'Successfully processed {processed_count} file emails for '
                f'user {user.username}'
            )

            if verbose or processed_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Processed {processed_count} file emails for "
                        f"{user.username}"
                    )
                )
        except Exception as e:
            logger.error(
                f'Failed to process file emails for user {user.username}: {e}'
            )
            if verbose:
                self.stdout.write(
                    self.style.ERROR(
                        f'Failed to process file emails for {user.username}: {e}'
                    )
                )
