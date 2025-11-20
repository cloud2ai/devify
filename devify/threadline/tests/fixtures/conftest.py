"""
Pytest configuration for Threadline API tests

This module provides pytest fixtures and configuration for testing
the Threadline API endpoints.
"""

import os
import sys
import django
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'devify.core.settings')

# Configure Django
django.setup()

import pytest
from django.contrib.auth.models import User
from django.test import Client
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from threadline.models import (
    Settings,
    EmailTask,
    EmailMessage,
    EmailAttachment,
    Issue,
    EmailTodo
)


@pytest.fixture
def api_client():
    """
    API client for testing REST endpoints
    """
    return APIClient()


@pytest.fixture
def django_client():
    """
    Django test client for testing non-API endpoints
    """
    return Client()


@pytest.fixture
def test_user():
    """
    Create a test user for authentication
    """
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={
            'email': 'test@example.com',
            'password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User'
        }
    )
    if not created:
        # Update password if user already exists
        user.set_password('testpass123')
        user.save()
    return user


@pytest.fixture
def test_user_2():
    """
    Create a second test user for permission testing
    """
    user, created = User.objects.get_or_create(
        username='testuser2',
        defaults={
            'email': 'test2@example.com',
            'password': 'testpass123',
            'first_name': 'Test2',
            'last_name': 'User2'
        }
    )
    if not created:
        # Update password if user already exists
        user.set_password('testpass123')
        user.save()
    return user


@pytest.fixture
def authenticated_api_client(api_client, test_user):
    """
    API client with authentication token
    """
    # Use force_authenticate for testing
    api_client.force_authenticate(user=test_user)
    return api_client


@pytest.fixture
def authenticated_api_client_2(api_client, test_user_2):
    """
    Second API client with authentication token for permission testing
    """
    # Use force_authenticate for testing
    api_client.force_authenticate(user=test_user_2)
    return api_client


@pytest.fixture
def test_setting(test_user):
    """
    Create a test setting
    """
    setting, created = Settings.objects.get_or_create(
        user=test_user,
        key='test_setting',
        defaults={
            'value': {'theme': 'dark', 'notifications': True},
            'description': 'Test setting for API testing',
            'is_active': True
        }
    )
    return setting


@pytest.fixture
def test_email_task(test_user):
    """
    Create a test email task
    """
    return EmailTask.objects.create(
        task_type=EmailTask.TaskType.IMAP_FETCH,
        status='running'
    )


@pytest.fixture
def test_email_message(test_user):
    """
    Create a test email message
    """
    from ..fixtures.factories import EmailMessageFactory
    return EmailMessageFactory(user=test_user)


@pytest.fixture
def test_email_attachment(test_user, test_email_message):
    """
    Create a test email attachment
    """
    return EmailAttachment.objects.create(
        user=test_user,
        email_message=test_email_message,
        filename='test_attachment.pdf',
        safe_filename='test_attachment.pdf',
        content_type='application/pdf',
        file_size=1024,
        file_path='/uploads/test_attachment.pdf',
        is_image=False
    )


@pytest.fixture
def test_issue(test_user, test_email_message):
    """
    Create a test issue
    """
    return Issue.objects.create(
        user=test_user,
        email_message=test_email_message,
        title='Test Issue',
        description='Test issue description',
        priority='medium',
        engine='jira',
        external_id='TEST-123',
        issue_url='https://jira.example.com/browse/TEST-123',
        metadata={'project': 'TEST', 'assignee': 'testuser'}
    )


@pytest.fixture
def test_email_todo(test_user, test_email_message):
    """
    Create a test email todo
    """
    return EmailTodo.objects.create(
        user=test_user,
        email_message=test_email_message,
        content='Test TODO item',
        is_completed=False,
        priority='medium',
        owner='Test Owner',
        location='Test Location',
        metadata={'source': 'test'}
    )
