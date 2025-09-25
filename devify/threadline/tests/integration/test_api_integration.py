"""
Integration tests for Threadline API

This module contains integration tests that test the complete API workflows
and interactions between different endpoints.
"""

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from threadline.models import Settings, EmailMessage, EmailAttachment
from ..fixtures.factories import (
    SettingsFactory,
    EmailMessageFactory,
    EmailAttachmentFactory,
    UserFactory
)


@pytest.mark.django_db
@pytest.mark.integration
class TestAPIWorkflows:
    """
    Integration tests for complete API workflows
    """

    def test_complete_settings_workflow(self, authenticated_api_client, test_user):
        """
        Test complete settings CRUD workflow
        """
        # 1. Create a setting
        url = reverse('settings-list')
        create_data = {
            'user_id': test_user.id,
            'key': 'workflow_test_setting',
            'value': {'theme': 'dark', 'language': 'en'},
            'description': 'Test setting for workflow',
            'is_active': True
        }
        response = authenticated_api_client.post(url, create_data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        setting_id = response.data['data']['id']

        # 2. Retrieve the setting
        url = reverse('settings-detail', kwargs={'pk': setting_id})
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['key'] == 'workflow_test_setting'
        assert response.data['data']['value'] == {'theme': 'dark', 'language': 'en'}

        # 3. Update the setting
        update_data = {
            'value': {'theme': 'light', 'language': 'zh-CN'},
            'description': 'Updated workflow test setting',
            'is_active': False
        }
        response = authenticated_api_client.put(url, update_data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['value'] == {'theme': 'light', 'language': 'zh-CN'}
        assert response.data['data']['is_active'] is False

        # 4. List settings to verify update
        url = reverse('settings-list')
        response = authenticated_api_client.get(url, {'is_active': 'false'})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']['list']) == 1
        assert response.data['data']['list'][0]['id'] == setting_id

        # 5. Delete the setting
        url = reverse('settings-detail', kwargs={'pk': setting_id})
        response = authenticated_api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # 6. Verify deletion
        response = authenticated_api_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_complete_threadlines_workflow(self, authenticated_api_client, test_user):
        """
        Test complete threadlines CRUD workflow
        """
        # Create an EmailTask first
        from .factories import EmailTaskFactory
        task = EmailTaskFactory(user=test_user)

        # 1. Create a threadline (email message)
        url = reverse('threadlines-list')
        create_data = {
            'user_id': test_user.id,
            'task_id': task.id,
            'message_id': 'workflow-test-message-123',
            'subject': 'Workflow Test Email',
            'sender': 'sender@example.com',
            'recipients': 'recipient@example.com',
            'received_at': '2024-01-01T10:00:00Z',
            'raw_content': 'Raw email content for workflow test',
            'html_content': '<p>HTML content for workflow test</p>',
            'text_content': 'Plain text content for workflow test'
        }
        response = authenticated_api_client.post(url, create_data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        threadline_id = response.data['data']['id']

        # 2. Retrieve the threadline
        url = reverse('threadlines-detail', kwargs={'pk': threadline_id})
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['subject'] == 'Workflow Test Email'
        assert response.data['data']['message_id'] == 'workflow-test-message-123'
        assert 'attachments' in response.data['data']

        # 3. Update the threadline with summary information
        update_data = {
            'subject': 'Updated Workflow Test Email',
            'summary_title': 'Important Email Summary',
            'summary_content': 'This is a summary of the workflow test email',
            'summary_priority': 'high',
            'llm_content': 'LLM processed content for workflow test'
        }
        response = authenticated_api_client.patch(url, update_data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['subject'] == 'Updated Workflow Test Email'
        assert response.data['data']['summary_title'] == 'Important Email Summary'

        # 4. List threadlines to verify update
        url = reverse('threadlines-list')
        response = authenticated_api_client.get(url, {'search': 'workflow'})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']['list']) == 1
        assert response.data['data']['list'][0]['id'] == threadline_id

        # 5. Create attachments for the threadline
        message = EmailMessage.objects.get(id=threadline_id)
        attachment1 = EmailAttachmentFactory(
            email_message=message,
            filename='workflow_attachment1.pdf',
            content_type='application/pdf'
        )
        attachment2 = EmailAttachmentFactory(
            email_message=message,
            filename='workflow_attachment2.jpg',
            content_type='image/jpeg'
        )

        # 6. Retrieve threadline with attachments
        url = reverse('threadlines-detail', kwargs={'pk': threadline_id})
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']['attachments']) == 2

        attachment_filenames = [att['filename'] for att in response.data['data']['attachments']]
        assert 'workflow_attachment1.pdf' in attachment_filenames
        assert 'workflow_attachment2.jpg' in attachment_filenames

        # 7. Update threadline status through workflow
        status_update_data = {'status': 'ocr_processing'}
        response = authenticated_api_client.patch(url, status_update_data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['status'] == 'ocr_processing'

        # 8. Complete the workflow
        final_status_data = {'status': 'completed'}
        response = authenticated_api_client.patch(url, final_status_data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['status'] == 'completed'

        # 9. Delete the threadline (should cascade delete attachments)
        response = authenticated_api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # 10. Verify deletion
        response = authenticated_api_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Verify attachments were also deleted
        assert not EmailAttachment.objects.filter(email_message=message).exists()

    def test_settings_and_threadlines_interaction(self, authenticated_api_client, test_user):
        """
        Test interaction between settings and threadlines
        """
        # 1. Create settings for email processing
        settings_url = reverse('settings-list')
        settings_data = {
            'key': 'email_processing_config',
            'value': {
                'auto_process': True,
                'notification_enabled': True,
                'default_priority': 'medium'
            },
            'description': 'Email processing configuration',
            'is_active': True
        }
        response = authenticated_api_client.post(settings_url, settings_data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        setting_id = response.data['data']['id']

        # Create an EmailTask first
        from .factories import EmailTaskFactory
        task = EmailTaskFactory(user=test_user)

        # 2. Create threadlines with different priorities
        threadlines_url = reverse('threadlines-list')

        high_priority_data = {
            'user_id': test_user.id,
            'task_id': task.id,
            'message_id': 'high-priority-message',
            'subject': 'High Priority Email',
            'sender': 'urgent@example.com',
            'recipients': 'manager@example.com',
            'received_at': '2024-01-01T10:00:00Z',
            'raw_content': 'Urgent content',
            'summary_priority': 'high'
        }
        response = authenticated_api_client.post(threadlines_url, high_priority_data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        high_priority_id = response.data['data']['id']

        low_priority_data = {
            'message_id': 'low-priority-message',
            'subject': 'Low Priority Email',
            'sender': 'newsletter@example.com',
            'recipients': 'user@example.com',
            'received_at': '2024-01-01T10:00:00Z',
            'raw_content': 'Newsletter content',
            'summary_priority': 'low'
        }
        response = authenticated_api_client.post(threadlines_url, low_priority_data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        low_priority_id = response.data['data']['id']

        # 3. Filter threadlines by priority
        response = authenticated_api_client.get(threadlines_url, {'search': 'priority'})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']['list']) == 2

        # 4. Update settings and verify impact
        settings_detail_url = reverse('settings-detail', kwargs={'pk': setting_id})
        updated_settings = {
            'value': {
                'auto_process': False,
                'notification_enabled': True,
                'default_priority': 'high'
            },
            'description': 'Updated email processing configuration',
            'is_active': True
        }
        response = authenticated_api_client.put(settings_detail_url, updated_settings, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['value']['auto_process'] is False

        # 5. Verify settings are still accessible
        response = authenticated_api_client.get(settings_detail_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['key'] == 'email_processing_config'

    def test_multi_user_data_isolation_workflow(self, authenticated_api_client, test_user, authenticated_api_client_2, test_user_2):
        """
        Test complete workflow ensuring data isolation between users
        """
        # User 1 creates settings and threadlines
        settings_url = reverse('settings-list')
        user1_settings = {
            'key': 'user1_config',
            'value': {'theme': 'dark'},
            'description': 'User 1 configuration'
        }
        response = authenticated_api_client.post(settings_url, user1_settings, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        user1_setting_id = response.data['data']['id']

        # Create EmailTask for user 1
        from .factories import EmailTaskFactory
        user1_task = EmailTaskFactory(user=test_user)

        threadlines_url = reverse('threadlines-list')
        user1_threadline = {
            'user_id': test_user.id,
            'task_id': user1_task.id,
            'message_id': 'user1-message',
            'subject': 'User 1 Message',
            'sender': 'user1@example.com',
            'recipients': 'recipient@example.com',
            'received_at': '2024-01-01T10:00:00Z',
            'raw_content': 'User 1 content'
        }
        response = authenticated_api_client.post(threadlines_url, user1_threadline, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        user1_threadline_id = response.data['data']['id']

        # User 2 creates settings and threadlines
        user2_settings = {
            'key': 'user2_config',
            'value': {'theme': 'light'},
            'description': 'User 2 configuration'
        }
        response = authenticated_api_client_2.post(settings_url, user2_settings, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        user2_setting_id = response.data['data']['id']

        # Create EmailTask for user 2
        user2_task = EmailTaskFactory(user=test_user_2)

        user2_threadline = {
            'user_id': test_user_2.id,
            'task_id': user2_task.id,
            'message_id': 'user2-message',
            'subject': 'User 2 Message',
            'sender': 'user2@example.com',
            'recipients': 'recipient@example.com',
            'received_at': '2024-01-01T10:00:00Z',
            'raw_content': 'User 2 content'
        }
        response = authenticated_api_client_2.post(threadlines_url, user2_threadline, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        user2_threadline_id = response.data['data']['id']

        # Verify User 1 can only see their own data
        response = authenticated_api_client.get(settings_url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']['list']) == 1
        assert response.data['data']['list'][0]['id'] == user1_setting_id

        response = authenticated_api_client.get(threadlines_url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']['list']) == 1
        assert response.data['data']['list'][0]['id'] == user1_threadline_id

        # Verify User 2 can only see their own data
        response = authenticated_api_client_2.get(settings_url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']['list']) == 1
        assert response.data['data']['list'][0]['id'] == user2_setting_id

        response = authenticated_api_client_2.get(threadlines_url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']['list']) == 1
        assert response.data['data']['list'][0]['id'] == user2_threadline_id

        # Verify cross-user access is denied
        user1_settings_detail = reverse('settings-detail', kwargs={'pk': user2_setting_id})
        response = authenticated_api_client.get(user1_settings_detail)
        assert response.status_code == status.HTTP_404_NOT_FOUND

        user1_threadline_detail = reverse('threadlines-detail', kwargs={'pk': user2_threadline_id})
        response = authenticated_api_client.get(user1_threadline_detail)
        assert response.status_code == status.HTTP_404_NOT_FOUND

        user2_settings_detail = reverse('settings-detail', kwargs={'pk': user1_setting_id})
        response = authenticated_api_client_2.get(user2_settings_detail)
        assert response.status_code == status.HTTP_404_NOT_FOUND

        user2_threadline_detail = reverse('threadlines-detail', kwargs={'pk': user1_threadline_id})
        response = authenticated_api_client_2.get(user2_threadline_detail)
        assert response.status_code == status.HTTP_404_NOT_FOUND
