"""
Performance tests for Threadline API

This module contains performance tests to ensure API endpoints
perform well with larger datasets.
"""

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
import time

from threadline.models import Settings, EmailMessage, EmailAttachment
from ..fixtures.factories import (
    SettingsFactory,
    EmailMessageFactory,
    EmailAttachmentFactory,
    EmailMessageWithAttachmentsFactory
)


@pytest.mark.django_db
@pytest.mark.performance
class TestPerformanceSettings:
    """
    Performance tests for Settings API endpoints
    """

    def test_settings_list_performance_large_dataset(self, authenticated_api_client, test_user):
        """
        Test settings list performance with large dataset
        """
        # Create 100 settings
        settings = SettingsFactory.create_batch(100, user=test_user)

        url = reverse('settings-list')

        start_time = time.time()
        response = authenticated_api_client.get(url, {'page_size': 50})
        end_time = time.time()

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']['list']) == 50
        assert response.data['data']['pagination']['total'] == 100

        # Should complete within reasonable time (adjust threshold as needed)
        execution_time = end_time - start_time
        assert execution_time < 1.0  # Should complete within 1 second

    def test_settings_search_performance(self, authenticated_api_client, test_user):
        """
        Test settings search performance
        """
        # Create settings with searchable content
        for i in range(50):
            SettingsFactory(
                user=test_user,
                key=f'config_{i}',
                description=f'Configuration setting {i} for testing'
            )

        url = reverse('settings-list')

        start_time = time.time()
        response = authenticated_api_client.get(url, {'search': 'config'})
        end_time = time.time()

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']['list']) == 50

        execution_time = end_time - start_time
        assert execution_time < 1.0

    def test_settings_filtering_performance(self, authenticated_api_client, test_user):
        """
        Test settings filtering performance
        """
        # Create mixed active/inactive settings
        SettingsFactory.create_batch(50, user=test_user, is_active=True)
        SettingsFactory.create_batch(50, user=test_user, is_active=False)

        url = reverse('settings-list')

        start_time = time.time()
        response = authenticated_api_client.get(url, {'is_active': 'true'})
        end_time = time.time()

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']['list']) == 50
        assert all(item['is_active'] for item in response.data['data']['list'])

        execution_time = end_time - start_time
        assert execution_time < 1.0


@pytest.mark.django_db
class TestPerformanceThreadlines:
    """
    Performance tests for Threadlines API endpoints
    """

    def test_threadlines_list_performance_large_dataset(self, authenticated_api_client, test_user):
        """
        Test threadlines list performance with large dataset
        """
        # Create 100 email messages
        messages = EmailMessageFactory.create_batch(100, user=test_user)

        url = reverse('threadlines-list')

        start_time = time.time()
        response = authenticated_api_client.get(url, {'page_size': 50})
        end_time = time.time()

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']['list']) == 50
        assert response.data['data']['pagination']['total'] == 100

        execution_time = end_time - start_time
        assert execution_time < 2.0  # Allow more time for complex queries with attachments

    def test_threadlines_with_attachments_performance(self, authenticated_api_client, test_user):
        """
        Test threadlines performance with attachments
        """
        # Create messages with attachments
        messages = []
        for i in range(20):
            message = EmailMessageFactory(user=test_user, subject=f'Message {i}')
            # Add 3 attachments per message
            EmailAttachmentFactory.create_batch(3, email_message=message)
            messages.append(message)

        url = reverse('threadlines-list')

        start_time = time.time()
        response = authenticated_api_client.get(url, {'page_size': 10})
        end_time = time.time()

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']['list']) == 10

        # Verify attachments are included
        for threadline in response.data['data']['list']:
            assert 'attachments' in threadline
            # Each message should have 3 attachments
            assert len(threadline['attachments']) == 3

        execution_time = end_time - start_time
        assert execution_time < 3.0  # Allow more time for complex queries with attachments

    def test_threadlines_search_performance(self, authenticated_api_client, test_user):
        """
        Test threadlines search performance
        """
        # Create messages with searchable content
        for i in range(100):
            EmailMessageFactory(
                user=test_user,
                subject=f'Important Meeting {i}',
                sender=f'sender{i}@company.com'
            )

        url = reverse('threadlines-list')

        start_time = time.time()
        response = authenticated_api_client.get(url, {'search': 'meeting'})
        end_time = time.time()

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']['list']) == 100

        execution_time = end_time - start_time
        assert execution_time < 2.0

    def test_threadlines_status_filter_performance(self, authenticated_api_client, test_user):
        """
        Test threadlines status filtering performance
        """
        # Create messages with different statuses
        statuses = ['fetched', 'ocr_processing', 'llm_summary_success', 'completed']
        for status in statuses:
            EmailMessageFactory.create_batch(25, user=test_user, status=status)

        url = reverse('threadlines-list')

        start_time = time.time()
        response = authenticated_api_client.get(url, {'status': 'fetched'})
        end_time = time.time()

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']['list']) == 25
        assert all(item['status'] == 'fetched' for item in response.data['data']['list'])

        execution_time = end_time - start_time
        assert execution_time < 2.0

    def test_threadlines_ordering_performance(self, authenticated_api_client, test_user):
        """
        Test threadlines ordering performance
        """
        # Create messages with different received_at times
        messages = EmailMessageFactory.create_batch(100, user=test_user)

        url = reverse('threadlines-list')

        start_time = time.time()
        response = authenticated_api_client.get(url, {'ordering': '-received_at', 'page_size': 50})
        end_time = time.time()

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']['list']) == 50

        execution_time = end_time - start_time
        assert execution_time < 2.0

    def test_threadlines_detail_with_attachments_performance(self, authenticated_api_client, test_user):
        """
        Test threadline detail performance with many attachments
        """
        # Create message with many attachments
        message = EmailMessageFactory(user=test_user)
        EmailAttachmentFactory.create_batch(20, email_message=message)

        url = reverse('threadlines-detail', kwargs={'pk': message.id})

        start_time = time.time()
        response = authenticated_api_client.get(url)
        end_time = time.time()

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']['attachments']) == 20

        execution_time = end_time - start_time
        assert execution_time < 1.0


@pytest.mark.django_db
class TestPerformancePagination:
    """
    Performance tests for pagination functionality
    """

    def test_large_pagination_performance(self, authenticated_api_client, test_user):
        """
        Test pagination performance with large datasets
        """
        # Create large dataset
        SettingsFactory.create_batch(1000, user=test_user)

        url = reverse('settings-list')

        # Test different page sizes
        page_sizes = [10, 25, 50, 100]

        for page_size in page_sizes:
            start_time = time.time()
            response = authenticated_api_client.get(url, {
                'page_size': page_size,
                'page': 1
            })
            end_time = time.time()

            assert response.status_code == status.HTTP_200_OK
            assert len(response.data['data']['list']) == page_size
            assert response.data['data']['pagination']['total'] == 1000

            execution_time = end_time - start_time
            assert execution_time < 1.0

    def test_deep_pagination_performance(self, authenticated_api_client, test_user):
        """
        Test performance of deep pagination (later pages)
        """
        # Create large dataset
        EmailMessageFactory.create_batch(500, user=test_user)

        url = reverse('threadlines-list')

        # Test deep pagination
        start_time = time.time()
        response = authenticated_api_client.get(url, {
            'page_size': 10,
            'page': 25  # Deep page
        })
        end_time = time.time()

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']['list']) == 10
        assert response.data['data']['pagination']['total'] == 500

        execution_time = end_time - start_time
        assert execution_time < 2.0


@pytest.mark.django_db
class TestPerformanceConcurrent:
    """
    Performance tests for concurrent access scenarios
    """

    def test_concurrent_read_performance(self, authenticated_api_client, test_user):
        """
        Test performance under concurrent read scenarios
        """
        # Create dataset
        EmailMessageFactory.create_batch(50, user=test_user)

        url = reverse('threadlines-list')

        # Simulate concurrent reads
        start_time = time.time()
        responses = []

        for _ in range(10):  # 10 concurrent requests
            response = authenticated_api_client.get(url, {'page_size': 25})
            responses.append(response)

        end_time = time.time()

        # All requests should succeed
        for response in responses:
            assert response.status_code == status.HTTP_200_OK

        execution_time = end_time - start_time
        assert execution_time < 5.0  # 10 concurrent requests should complete within 5 seconds

    def test_mixed_operation_performance(self, authenticated_api_client, test_user):
        """
        Test performance of mixed read/write operations
        """
        # Create initial dataset
        EmailMessageFactory.create_batch(20, user=test_user)

        url = reverse('threadlines-list')

        start_time = time.time()

        # Mix of read operations
        for _ in range(5):
            response = authenticated_api_client.get(url, {'page_size': 10})
            assert response.status_code == status.HTTP_200_OK

            # Create new message
            new_message = EmailMessageFactory(user=test_user)

            # Retrieve the new message
            detail_url = reverse('threadlines-detail', kwargs={'pk': new_message.id})
            response = authenticated_api_client.get(detail_url)
            assert response.status_code == status.HTTP_200_OK

        end_time = time.time()

        execution_time = end_time - start_time
        assert execution_time < 10.0  # Mixed operations should complete within 10 seconds
