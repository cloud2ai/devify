"""
Utility functions for Haraka email integration testing

This module provides helper functions for:
- Creating test users with auto_assign configuration
- Sending EML files to Haraka
- Triggering email fetch tasks
- Waiting for workflow completion
- Verifying test results
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path
from io import StringIO

import django

project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from django.core.management import call_command
from django.conf import settings

from threadline.models import Settings, EmailMessage, EmailAlias
from threadline.tasks.email_fetch import haraka_email_fetch


# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(title):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{'=' * 60}")
    print(f"{title}")
    print(f"{'=' * 60}{Colors.END}\n")


def print_step(step_num, title):
    """Print a step header"""
    print(f"{Colors.BOLD}[Step {step_num}/5] {title}{Colors.END}")


def print_success(message):
    """Print a success message"""
    print(f"  {Colors.GREEN}✓{Colors.END} {message}")


def print_error(message):
    """Print an error message"""
    print(f"  {Colors.RED}✗{Colors.END} {message}")


def print_info(message):
    """Print an info message"""
    print(f"  {Colors.BLUE}ℹ{Colors.END} {message}")


def create_user_with_config(username, email_alias=None, password='test123'):
    """
    Create a test user with auto_assign email configuration

    Args:
        username: Username for the new user
        email_alias: Optional email alias
        password: User password

    Returns:
        User: Created user instance
    """
    user = User.objects.create_user(
        username=username,
        email=f'{username}@test.com',
        password=password,
        is_active=True
    )

    out = StringIO()
    call_command(
        'init_threadline_settings',
        user=username,
        language='en-US',
        scene='chat',
        force=True,
        stdout=out,
        stderr=out
    )

    email_config = Settings.objects.get(user=user, key='email_config')
    email_config.value['mode'] = 'auto_assign'
    email_config.save()

    if email_alias:
        EmailAlias.objects.create(
            user=user,
            alias=email_alias,
            is_active=True
        )

    return user


def create_test_users():
    """
    Create 3 test users with auto_assign mode

    Returns:
        list: List of user information dictionaries
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    users = []

    user1 = create_user_with_config(
        username=f'testuser1_{timestamp}',
        email_alias=None
    )
    users.append({
        'user': user1,
        'email': f'testuser1_{timestamp}@{settings.AUTO_ASSIGN_EMAIL_DOMAIN}',
        'eml_file': 'gmail_email.eml',
        'description': 'User with username-based email'
    })
    print_success(f"Created user: {user1.username}")

    alias2 = f'testalias2_{timestamp}'
    user2 = create_user_with_config(
        username=f'testuser2_{timestamp}',
        email_alias=alias2
    )
    users.append({
        'user': user2,
        'email': f'{alias2}@{settings.AUTO_ASSIGN_EMAIL_DOMAIN}',
        'eml_file': 'iphone_email.eml',
        'description': 'User with email alias'
    })
    print_success(
        f"Created user: {user2.username} (alias: {alias2})"
    )

    alias3 = f'testalias3_{timestamp}'
    user3 = create_user_with_config(
        username=f'testuser3_{timestamp}',
        email_alias=alias3
    )
    users.append({
        'user': user3,
        'email': f'{alias3}@{settings.AUTO_ASSIGN_EMAIL_DOMAIN}',
        'eml_file': 'wechat_email.eml',
        'description': 'User with email alias'
    })
    print_success(
        f"Created user: {user3.username} (alias: {alias3})"
    )

    print_info(f"Total: {len(users)} users created successfully\n")
    return users


def get_eml_path(eml_filename):
    """
    Get full path to EML sample file

    Args:
        eml_filename: EML file name

    Returns:
        Path: Full path to EML file
    """
    base_dir = Path(__file__).resolve().parent.parent.parent
    eml_path = base_dir / 'fixtures' / 'eml_samples' / eml_filename

    if not eml_path.exists():
        raise FileNotFoundError(f"EML file not found: {eml_path}")

    return eml_path


def send_eml_to_haraka(eml_path, recipient_email):
    """
    Send EML file to Haraka using Django management command

    Args:
        eml_path: Path to EML file
        recipient_email: Recipient email address

    Returns:
        bool: True if successful
    """
    try:
        out = StringIO()
        call_command(
            'send_test_email',
            recipient_email,
            eml_file=str(eml_path),
            server='haraka',
            port=25,
            stdout=out,
            stderr=out
        )
        return True
    except Exception as e:
        print_error(f"Failed to send email: {e}")
        return False


def send_test_emails(users):
    """
    Send test emails to all users

    Args:
        users: List of user information dictionaries

    Returns:
        list: List of sent email information
    """
    sent_emails = []

    for user_info in users:
        eml_path = get_eml_path(user_info['eml_file'])
        success = send_eml_to_haraka(eml_path, user_info['email'])

        if success:
            print_success(
                f"Sent {user_info['eml_file']} → {user_info['email']}"
            )
            sent_emails.append(user_info)
        else:
            print_error(
                f"Failed to send {user_info['eml_file']} → "
                f"{user_info['email']}"
            )

    print_info(f"Total: {len(sent_emails)} emails sent successfully\n")
    return sent_emails


def trigger_email_fetch():
    """
    Trigger haraka_email_fetch task

    Returns:
        dict: Task result
    """
    try:
        result = haraka_email_fetch.apply()
        task_result = result.result

        print_success("Called haraka_email_fetch task")

        if task_result:
            print_success(
                f"Fetched {task_result.get('emails_processed', 0)} emails"
            )

        print_info("Email fetch completed\n")
        return task_result
    except Exception as e:
        print_error(f"Failed to trigger email fetch: {e}")
        return None


def get_latest_email(user):
    """
    Get the latest email for a user

    Args:
        user: User instance

    Returns:
        EmailMessage: Latest email message or None
    """
    try:
        return EmailMessage.objects.filter(
            user=user
        ).order_by('-created_at').first()
    except Exception:
        return None


def format_time(seconds):
    """Format seconds into readable time string"""
    if seconds < 60:
        return f"{int(seconds)}s"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}m {secs}s"


def print_progress(sent_emails, email_results, start_time):
    """
    Print progress of email processing

    Args:
        sent_emails: List of sent email info
        email_results: List of completed email results
        start_time: Start time of monitoring
    """
    elapsed = time.time() - start_time
    time_str = format_time(elapsed)

    progress_parts = []
    for user_info in sent_emails:
        user = user_info['user']

        result = next(
            (r for r in email_results if r['user'].id == user.id),
            None
        )

        if result:
            status = result['email'].status
            progress_parts.append(
                f"{user.username}: {Colors.GREEN}{status}{Colors.END}"
            )
        else:
            email = get_latest_email(user)
            if email:
                status = email.status
                color = Colors.YELLOW if status == 'processing' else Colors.BLUE
                progress_parts.append(
                    f"{user.username}: {color}{status}{Colors.END}"
                )
            else:
                progress_parts.append(
                    f"{user.username}: {Colors.YELLOW}waiting{Colors.END}"
                )

    print(
        f"\r  [{time_str}] {' | '.join(progress_parts)}",
        end='',
        flush=True
    )


def wait_for_all_emails(sent_emails, timeout=300):
    """
    Wait for all emails to complete processing

    Args:
        sent_emails: List of sent email information
        timeout: Maximum wait time in seconds

    Returns:
        list: List of email results
    """
    start_time = time.time()
    email_results = []

    print_info(f"Monitoring email processing (timeout: {timeout}s)...")

    while time.time() - start_time < timeout:
        all_done = True

        for user_info in sent_emails:
            user = user_info['user']

            if any(r['user'].id == user.id for r in email_results):
                continue

            email = get_latest_email(user)

            if email and email.status in ['success', 'failed']:
                email_results.append({
                    'user': user,
                    'email': email,
                    'user_info': user_info,
                    'elapsed': time.time() - start_time
                })
            else:
                all_done = False

        print_progress(sent_emails, email_results, start_time)

        if all_done and len(email_results) == len(sent_emails):
            break

        time.sleep(5)

    print()
    print_info(
        f"Processing completed: {len(email_results)}/{len(sent_emails)} "
        f"emails\n"
    )

    return email_results


def verify_results(email_results):
    """
    Verify test results

    Args:
        email_results: List of email result dictionaries

    Returns:
        list: List of verification results
    """
    results = []

    for result in email_results:
        email = result['email']
        user = result['user']
        user_info = result['user_info']

        verification = {
            'user': user.username,
            'email_id': email.id,
            'status': email.status,
            'elapsed': result['elapsed'],
            'checks': {
                'status_success': email.status == 'success',
                'has_subject': bool(email.subject),
                'has_content': bool(
                    email.text_content or email.html_content
                ),
                'has_attachments': email.attachments.exists(),
                'attachments_count': email.attachments.count()
            }
        }

        results.append(verification)

    return results


def print_verification_result(verification):
    """Print verification result for a single email"""
    print(f"\n  User: {Colors.BOLD}{verification['user']}{Colors.END}")

    checks = verification['checks']

    if checks['status_success']:
        print_success(f"Status: {verification['status'].upper()}")
    else:
        print_error(f"Status: {verification['status'].upper()}")

    email = EmailMessage.objects.get(id=verification['email_id'])

    if checks['has_subject']:
        print_success(f"Subject: {email.subject[:50]}...")
    else:
        print_error("Subject: Missing")

    if checks['has_attachments']:
        print_success(
            f"Attachments: {checks['attachments_count']} files"
        )
    else:
        print_info("Attachments: None")

    print_info(f"Processing time: {format_time(verification['elapsed'])}")


def print_report(test_results):
    """
    Print final test report

    Args:
        test_results: List of verification results
    """
    print_header("Test Results Summary")

    total = len(test_results)
    success = sum(
        1 for r in test_results if r['checks']['status_success']
    )
    failed = total - success

    avg_time = sum(r['elapsed'] for r in test_results) / total if total > 0 else 0

    print(f"Total tests: {total}")
    print(f"Success: {Colors.GREEN}{success} ✅{Colors.END}")
    print(f"Failed: {Colors.RED}{failed}{Colors.END}")
    print(f"Average processing time: {format_time(avg_time)}")

    if failed == 0:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✅ All tests passed!{Colors.END}\n")
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}❌ Some tests failed!{Colors.END}\n")

    print("=" * 60 + "\n")


def cleanup_test_users(user_ids):
    """
    Clean up test users and related data

    Args:
        user_ids: List of user IDs to delete
    """
    try:
        deleted_count = User.objects.filter(id__in=user_ids).delete()[0]
        print_success(f"Cleaned up {deleted_count} test users")
    except Exception as e:
        print_error(f"Failed to cleanup: {e}")
