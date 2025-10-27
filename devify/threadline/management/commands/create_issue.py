"""
Django management command for creating JIRA issues from emails.

This command directly creates JIRA issues from existing email messages,
bypassing the full email processing workflow. It's designed for debugging
and testing the issue creation functionality.

Usage:
    # Create issue for a specific email
    python manage.py create_issue --email-id 123

    # Create issue with force flag
    python manage.py create_issue --email-id 123 --force

    # Enable verbose output
    python manage.py create_issue --email-id 123 --verbose

    # Enable debug logging
    python manage.py create_issue --email-id 123 --debug
"""

import logging

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from threadline.models import EmailMessage, Settings
from threadline.utils.issues.jira_handler import JiraIssueHandler

# Initialize logger for this module
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Command for creating JIRA issues from emails.

    This command directly calls JiraIssueHandler to create issues,
    bypassing the workflow system entirely. It's designed for
    debugging and testing the issue creation functionality.
    """
    help = "Create JIRA issue from an existing email message"

    def add_arguments(self, parser):
        """
        Add command line arguments for the management command.

        Args:
            parser: ArgumentParser instance to add arguments to
        """
        parser.add_argument(
            "--email-id",
            type=int,
            required=True,
            help="Email ID to create issue for"
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force issue creation even if issue already exists"
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Enable verbose output"
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Enable debug logging for detailed output"
        )

    def handle(self, *args, **options):
        """
        Handle the command logic for creating JIRA issues.

        Args:
            *args: Variable length argument list
            **options: Keyword arguments from command line options
        """
        email_id = options["email_id"]
        force = options["force"]
        verbose = options["verbose"]
        debug = options["debug"]

        # Set debug logging level if debug flag is enabled
        if debug:
            logging.getLogger().setLevel(logging.DEBUG)
            logger.info("Debug logging enabled")

        logger.info(f"Creating JIRA issue for email ID={email_id}")

        try:
            # Get the email message
            email = EmailMessage.objects.get(id=email_id)
            user = email.user
            logger.info(
                f"Found email ID={email_id} for user: {user.username}"
            )
        except EmailMessage.DoesNotExist:
            raise CommandError(f"Email ID {email_id} not found")

        try:
            # Get user's issue configuration
            issue_config = Settings.get_user_config(
                email.user, "issue_config"
            )
            logger.info(
                f"Loaded issue configuration for user {user.username}"
            )
        except ValueError as e:
            error_msg = (
                f"User {user.username} has no issue_config setting. "
                f"Please initialize it first using:\n"
                f"  python manage.py init_threadline_settings --user {user.username}"
            )
            self.stdout.write(
                self.style.ERROR(f"❌ {error_msg}")
            )
            raise CommandError(error_msg)

        try:
            # Prepare issue data
            summary_title = (
                email.summary_title or email.subject or "Email Issue"
            )
            summary_content = (
                email.summary_content or email.body or "No content"
            )

            issue_data = {
                "title": summary_title,
                "description": summary_content,
                "priority": issue_config.get("jira", {}).get(
                    "default_priority", "Medium"
                ),
            }

            # Prepare email data
            email_data = {
                "id": email_id,
                "summary_title": summary_title,
                "summary_content": summary_content,
                "llm_content": email.llm_content or "",
                "subject": email.subject or "",
                "metadata": email.metadata or {},
            }

            # Get attachments (must match workflow_prepare structure)
            attachments = []
            for att in email.attachments.all():
                attachments.append({
                    "id": str(att.id),
                    "filename": att.filename,
                    "safe_filename": att.safe_filename,
                    "content_type": att.content_type,
                    "file_size": att.file_size,
                    "file_path": att.file_path,
                    "is_image": att.is_image,
                    "ocr_content": att.ocr_content or None,
                    "llm_content": att.llm_content or None,
                })

            if verbose:
                self.stdout.write(f"📧 Email: {email.subject}")
                self.stdout.write(f"👤 User: {user.username}")
                self.stdout.write(f"📝 Title: {summary_title[:50]}...")
                self.stdout.write(f"📎 Attachments: {len(attachments)} files")

            # Create JIRA issue
            jira_handler = JiraIssueHandler(issue_config)

            logger.info(
                f"Creating JIRA issue with title: {summary_title[:50]}..."
            )

            issue_key = jira_handler.create_issue(
                issue_data=issue_data,
                email_data=email_data,
                attachments=attachments,
                force=force
            )

            if issue_key:
                logger.info(f"JIRA issue created successfully: {issue_key}")

                # Upload attachments
                upload_result = jira_handler.upload_attachments(
                    issue_key=issue_key,
                    attachments=attachments
                )
                logger.info(
                    f"Uploaded {upload_result['uploaded_count']} attachments "
                    f"to JIRA {issue_key}"
                )

                # Get issue URL
                issue_url = jira_handler.get_issue_url(issue_key)

                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ Successfully created JIRA issue: {issue_key}"
                    )
                )

                if verbose:
                    self.stdout.write(f"🔗 JIRA URL: {issue_url}")
                    self.stdout.write(f"📋 Issue Key: {issue_key}")
                    self.stdout.write(f"📝 Title: {summary_title}")

                    # Show JIRA configuration details
                    jira_config = issue_config.get("jira", {})
                    if "project" in jira_config:
                        self.stdout.write(
                            f"🏗️ Project: {jira_config['project']}"
                        )
                    if "default_priority" in jira_config:
                        self.stdout.write(
                            f"⚡ Priority: {jira_config['default_priority']}"
                        )
            else:
                logger.error("JIRA issue creation failed")
                self.stdout.write(
                    self.style.ERROR(
                        f"❌ Failed to create JIRA issue for email "
                        f"ID={email_id}"
                    )
                )
                raise CommandError("JIRA issue creation failed")

        except Exception as e:
            logger.error(
                f"Failed to create JIRA issue for email ID={email_id}: {e}",
                exc_info=True
            )
            self.stdout.write(
                self.style.ERROR(
                    f"❌ Failed to create JIRA issue for email "
                    f"ID={email_id}: {e}"
                )
            )
            raise CommandError(f"Failed to create JIRA issue: {e}")
