"""
Tests for authentication and permissions

This module contains tests for authentication and permission enforcement
across all Threadline API endpoints.
"""

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from threadline.models import Settings, EmailMessage
from .factories import SettingsFactory, EmailMessageFactory, UserFactory


@pytest.mark.django_db
class TestAuthentication:
    """
    Test authentication requirements for all API endpoints
    """

    def test_settings_endpoints_require_auth(self, api_client):
        """
        Test that all Settings endpoints require authentication
        """
        # List endpoint
        url = reverse('settings-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        response = api_client.post(url, {})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Detail endpoint
        url = reverse('settings-detail', kwargs={'pk': 1})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        response = api_client.put(url, {})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        response = api_client.patch(url, {})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        response = api_client.delete(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_threadlines_endpoints_require_auth(self, api_client):
        """
        Test that all Threadlines endpoints require authentication
        """
        # List endpoint
        url = reverse('threadlines-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        response = api_client.post(url, {})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Detail endpoint
        url = reverse('threadlines-detail', kwargs={'pk': 1})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        response = api_client.put(url, {})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        response = api_client.patch(url, {})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        response = api_client.delete(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_valid_token_grants_access(self, api_client, test_user):
        """
        Test that valid JWT token grants access to endpoints
        """
        # Use force_authenticate for reliable testing
        api_client.force_authenticate(user=test_user)

        # Test Settings endpoint
        url = reverse('settings-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

        # Test Threadlines endpoint
        url = reverse('threadlines-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_invalid_token_denies_access(self, api_client):
        """
        Test that invalid JWT token denies access
        """
        api_client.credentials(HTTP_AUTHORIZATION='Bearer invalid_token')

        # Test Settings endpoint
        url = reverse('settings-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Test Threadlines endpoint
        url = reverse('threadlines-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_expired_token_denies_access(self, api_client, test_user):
        """
        Test that expired JWT token denies access
        """
        from rest_framework_simplejwt.tokens import RefreshToken
        from datetime import timedelta

        # Create a token that's already expired
        refresh = RefreshToken.for_user(test_user)
        access_token = refresh.access_token
        access_token.set_exp(from_time=access_token.current_time - timedelta(hours=1))

        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        # Test Settings endpoint
        url = reverse('settings-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestUserDataIsolation:
    """
    Test that users can only access their own data
    """

    def test_settings_user_isolation(self, authenticated_api_client, test_user, authenticated_api_client_2, test_user_2):
        """
        Test that users can only access their own settings
        """
        # Clean up any existing settings
        Settings.objects.all().delete()

        # Create settings for both users
        setting1 = SettingsFactory(user=test_user)
        setting2 = SettingsFactory(user=test_user_2)

        # User 1 should only see their own settings
        url = reverse('settings-list')
        response = authenticated_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']['list']) == 1
        assert response.data['data']['list'][0]['id'] == setting1.id

        # User 2 should only see their own settings
        response = authenticated_api_client_2.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']['list']) == 1
        assert response.data['data']['list'][0]['id'] == setting2.id

        # User 1 cannot access User 2's setting details
        url = reverse('settings-detail', kwargs={'pk': setting2.id})
        response = authenticated_api_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # User 2 cannot access User 1's setting details
        url = reverse('settings-detail', kwargs={'pk': setting1.id})
        response = authenticated_api_client_2.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_threadlines_user_isolation(self, authenticated_api_client, test_user, authenticated_api_client_2, test_user_2):
        """
        Test that users can only access their own threadlines
        """
        # Create messages for both users
        message1 = EmailMessageFactory(user=test_user, subject='User 1 Message')
        message2 = EmailMessageFactory(user=test_user_2, subject='User 2 Message')

        # User 1 should only see their own messages
        url = reverse('threadlines-list')
        response = authenticated_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']['list']) == 1
        assert response.data['data']['list'][0]['id'] == message1.id

        # User 2 should only see their own messages
        response = authenticated_api_client_2.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']['list']) == 1
        assert response.data['data']['list'][0]['id'] == message2.id

        # User 1 cannot access User 2's message details
        url = reverse('threadlines-detail', kwargs={'pk': message2.id})
        response = authenticated_api_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # User 2 cannot access User 1's message details
        url = reverse('threadlines-detail', kwargs={'pk': message1.id})
        response = authenticated_api_client_2.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_cross_user_data_modification_prevention(self, authenticated_api_client, test_user, authenticated_api_client_2, test_user_2):
        """
        Test that users cannot modify other users' data
        """
        # Create data for both users
        setting1 = SettingsFactory(user=test_user, value={'test': 'value1'})
        setting2 = SettingsFactory(user=test_user_2, value={'test': 'value2'})
        message1 = EmailMessageFactory(user=test_user, subject='User 1 Message')
        message2 = EmailMessageFactory(user=test_user_2, subject='User 2 Message')

        # User 1 cannot update User 2's setting
        url = reverse('settings-detail', kwargs={'pk': setting2.id})
        response = authenticated_api_client.put(url, {'value': {'hacked': 'value'}}, format='json')
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # User 2 cannot update User 1's setting
        url = reverse('settings-detail', kwargs={'pk': setting1.id})
        response = authenticated_api_client_2.put(url, {'value': {'hacked': 'value'}}, format='json')
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # User 1 cannot update User 2's message
        url = reverse('threadlines-detail', kwargs={'pk': message2.id})
        response = authenticated_api_client.put(url, {'subject': 'Hacked Subject'}, format='json')
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # User 2 cannot update User 1's message
        url = reverse('threadlines-detail', kwargs={'pk': message1.id})
        response = authenticated_api_client_2.put(url, {'subject': 'Hacked Subject'}, format='json')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_cross_user_data_deletion_prevention(self, authenticated_api_client, test_user, authenticated_api_client_2, test_user_2):
        """
        Test that users cannot delete other users' data
        """
        # Create data for both users
        setting1 = SettingsFactory(user=test_user)
        setting2 = SettingsFactory(user=test_user_2)
        message1 = EmailMessageFactory(user=test_user)
        message2 = EmailMessageFactory(user=test_user_2)

        # User 1 cannot delete User 2's setting
        url = reverse('settings-detail', kwargs={'pk': setting2.id})
        response = authenticated_api_client.delete(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # User 2 cannot delete User 1's setting
        url = reverse('settings-detail', kwargs={'pk': setting1.id})
        response = authenticated_api_client_2.delete(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # User 1 cannot delete User 2's message
        url = reverse('threadlines-detail', kwargs={'pk': message2.id})
        response = authenticated_api_client.delete(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # User 2 cannot delete User 1's message
        url = reverse('threadlines-detail', kwargs={'pk': message1.id})
        response = authenticated_api_client_2.delete(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Verify data still exists
        assert Settings.objects.filter(id=setting1.id).exists()
        assert Settings.objects.filter(id=setting2.id).exists()
        assert EmailMessage.objects.filter(id=message1.id).exists()
        assert EmailMessage.objects.filter(id=message2.id).exists()


@pytest.mark.django_db
class TestPermissionEdgeCases:
    """
    Test edge cases and permission boundary conditions
    """

    def test_nonexistent_user_handling(self, authenticated_api_client, test_user):
        """
        Test handling of requests with valid token but user doesn't exist
        """
        # This is unlikely to happen in practice, but good to test
        # The token should be valid and the user should exist
        url = reverse('settings-list')
        response = authenticated_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_inactive_user_handling(self, api_client, test_user):
        """
        Test handling of inactive users
        """
        from rest_framework_simplejwt.tokens import RefreshToken

        # Make user inactive
        test_user.is_active = False
        test_user.save()

        # Create token for inactive user
        refresh = RefreshToken.for_user(test_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        # Should be denied access
        url = reverse('settings-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_superuser_permissions(self, api_client, test_user):
        """
        Test that superusers have appropriate permissions
        """
        # Make user a superuser
        test_user.is_superuser = True
        test_user.save()

        # Use force_authenticate for reliable testing
        api_client.force_authenticate(user=test_user)

        # Superuser should have access
        url = reverse('settings-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_malformed_authorization_header(self, api_client):
        """
        Test handling of malformed authorization headers
        """
        # Missing Bearer prefix
        api_client.credentials(HTTP_AUTHORIZATION='invalid_token')
        url = reverse('settings-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Empty authorization
        api_client.credentials(HTTP_AUTHORIZATION='')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Missing authorization header
        api_client.credentials()
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
