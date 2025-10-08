"""
Django management command for sending test emails

This command allows sending test emails with or without attachments
to specified email addresses for testing email processing functionality.
"""

import os
import smtplib
import tempfile
import time
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    """
    Django management command for sending test emails
    """
    help = 'Send test emails with or without attachments for testing'

    def add_arguments(self, parser):
        """
        Add command line arguments
        """
        parser.add_argument(
            'to_email',
            type=str,
            help='Email address to send the test email to'
        )
        parser.add_argument(
            '-s', '--subject',
            type=str,
            default='Test Email from Devify',
            help='Subject of the email (default: Test Email from Devify)'
        )
        parser.add_argument(
            '-b', '--body',
            type=str,
            default='This is a test email sent from Devify system.',
            help='Body content of the email'
        )
        parser.add_argument(
            '-a', '--attachment',
            type=str,
            help='Path to attachment file to include'
        )
        parser.add_argument(
            '--create-attachment',
            action='store_true',
            help='Create a temporary attachment file for testing'
        )
        parser.add_argument(
            '--server',
            type=str,
            default='haraka',
            help='SMTP server hostname (default: haraka)'
        )
        parser.add_argument(
            '--port',
            type=int,
            default=25,
            help='SMTP server port (default: 25)'
        )
        parser.add_argument(
            '--eml-file',
            type=str,
            help='Path to .eml file to send (ignores other options)'
        )

    def handle(self, *args, **options):
        """
        Handle the command execution
        """
        eml_file = options.get('eml_file')
        smtp_server = options['server']
        smtp_port = options['port']

        # Send from .eml file if provided
        if eml_file:
            to_email = options.get('to_email')
            success = self._send_from_eml(
                eml_file=eml_file,
                smtp_server=smtp_server,
                smtp_port=smtp_port,
                override_to=to_email
            )
            if success:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'EML file sent successfully: {eml_file}'
                    )
                )
            else:
                raise CommandError('Failed to send EML file')
            return

        # Original flow: construct email
        to_email = options['to_email']
        subject = options['subject']
        body = options['body']
        attachment_path = options['attachment']
        create_attachment = options['create_attachment']

        # Create temporary attachment if requested
        if create_attachment and not attachment_path:
            attachment_path = self._create_temp_attachment()

        # Send the email
        success = self._send_email(
            to_email=to_email,
            subject=subject,
            body=body,
            attachment_path=attachment_path,
            smtp_server=smtp_server,
            smtp_port=smtp_port
        )

        if success:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Test email sent successfully to: {to_email}'
                )
            )
        else:
            raise CommandError('Failed to send test email')

    def _create_temp_attachment(self):
        """
        Create a temporary attachment file for testing
        """
        try:
            # Create a temporary file with some test content
            temp_file = tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.txt',
                delete=False,
                prefix='test_attachment_'
            )

            test_content = """This is a test attachment file.
Created by Devify test email command.
Timestamp: {timestamp}
""".format(timestamp=time.strftime('%Y-%m-%d %H:%M:%S'))

            temp_file.write(test_content)
            temp_file.close()

            self.stdout.write(
                f'Created temporary attachment: {temp_file.name}'
            )
            return temp_file.name

        except Exception as e:
            self.stderr.write(f'Error creating temporary attachment: {e}')
            return None

    def _send_email(self, to_email, subject, body, attachment_path=None,
                   smtp_server='haraka', smtp_port=25):
        """
        Send email with optional attachment

        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body content
            attachment_path: Path to attachment file (optional)
            smtp_server: SMTP server hostname
            smtp_port: SMTP server port

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = 'test@example.com'
            msg['To'] = to_email
            msg['Subject'] = subject

            # Add body
            msg.attach(MIMEText(body, 'plain'))

            # Add attachment if provided
            if attachment_path and os.path.exists(attachment_path):
                try:
                    with open(attachment_path, 'rb') as attachment:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {os.path.basename(attachment_path)}',
                    )
                    msg.attach(part)
                    self.stdout.write(f'Added attachment: {attachment_path}')
                except Exception as e:
                    self.stderr.write(f'Error adding attachment: {e}')
                    return False
            elif attachment_path:
                self.stderr.write(f'Attachment file not found: {attachment_path}')
                return False

            # Send email
            try:
                server = smtplib.SMTP(smtp_server, smtp_port)
                server.send_message(msg)
                server.quit()

                self.stdout.write(f'Email sent successfully to: {to_email}')
                self.stdout.write(f'Subject: {subject}')
                return True

            except Exception as e:
                self.stderr.write(f'Error sending email: {e}')
                return False

        except Exception as e:
            self.stderr.write(f'Error creating email: {e}')
            return False

    def _send_from_eml(self, eml_file, smtp_server='haraka',
                      smtp_port=25, override_to=None):
        """
        Send email from .eml file.

        Args:
            eml_file: Path to .eml file
            smtp_server: SMTP server hostname
            smtp_port: SMTP server port
            override_to: Override recipient address (optional)

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Read .eml file
            if not os.path.exists(eml_file):
                self.stderr.write(f'EML file not found: {eml_file}')
                return False

            with open(eml_file, 'rb') as f:
                eml_content = f.read()

            # Parse email message
            from email import message_from_bytes
            msg = message_from_bytes(eml_content)

            # Extract sender and recipients
            from_addr = msg.get('From', 'test@example.com')

            # Use override recipient if provided
            if override_to:
                to_addrs = [override_to]
                # Replace To header in message
                msg.replace_header('To', override_to)
                eml_content = msg.as_bytes()
            else:
                to_addrs = msg.get('To', '').split(',')
                to_addrs = [addr.strip() for addr in to_addrs if addr.strip()]

            if not to_addrs:
                self.stderr.write('No recipient found in EML file')
                return False

            # Send email
            try:
                server = smtplib.SMTP(smtp_server, smtp_port)
                server.sendmail(from_addr, to_addrs, eml_content)
                server.quit()

                self.stdout.write(f'EML file sent successfully')
                self.stdout.write(f'From: {from_addr}')
                self.stdout.write(f'To: {", ".join(to_addrs)}')
                self.stdout.write(f'Subject: {msg.get("Subject", "N/A")}')
                return True

            except Exception as e:
                self.stderr.write(f'Error sending EML: {e}')
                return False

        except Exception as e:
            self.stderr.write(f'Error reading EML file: {e}')
            return False
