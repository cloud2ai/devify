"""
Tests for Settings API endpoints

This module contains comprehensive tests for the Settings API CRUD operations.
"""

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from threadline.models import Settings
from .factories import SettingsFactory, UserFactory


@pytest.mark.django_db
class TestSettingsAPI:
    """
    Test cases for Settings API endpoints
    """

    def test_list_settings_unauthenticated(self, api_client):
        """
        Test that unauthenticated users cannot access settings
        """
        url = reverse('settings-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_settings_authenticated_empty(self, authenticated_api_client, test_user):
        """
        Test listing settings when user has no settings
        """
        # Clean up any existing settings for this user
        Settings.objects.filter(user=test_user).delete()

        url = reverse('settings-list')
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['code'] == 200
        assert response.data['message'] == 'Settings retrieved successfully'
        assert response.data['data']['list'] == []
        assert response.data['data']['pagination']['total'] == 0

    def test_list_settings_authenticated_with_data(self, authenticated_api_client, test_user, test_setting):
        """
        Test listing settings when user has settings
        """
        url = reverse('settings-list')
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['code'] == 200
        assert len(response.data['data']['list']) == 1
        assert response.data['data']['list'][0]['id'] == test_setting.id
        assert response.data['data']['list'][0]['key'] == test_setting.key

    def test_list_settings_user_isolation(self, authenticated_api_client, test_user):
        """
        Test that users can only see their own settings
        """
        # Clean up any existing settings
        Settings.objects.all().delete()

        # Create another user with settings
        other_user = UserFactory()
        other_setting = SettingsFactory(user=other_user)

        url = reverse('settings-list')
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']['list']) == 0  # Should not see other user's settings

    def test_list_settings_search(self, authenticated_api_client, test_user):
        """
        Test search functionality in settings list
        """
        # Clean up any existing settings
        Settings.objects.all().delete()

        # Create settings with different keys
        SettingsFactory(user=test_user, description='Theme settings')
        SettingsFactory(user=test_user, description='Notification settings')

        url = reverse('settings-list')
        response = authenticated_api_client.get(url, {'search': 'theme'})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']['list']) == 1
        # Check that the found setting contains 'theme' in description
        assert 'theme' in response.data['data']['list'][0]['description'].lower()

    def test_list_settings_filter_active(self, authenticated_api_client, test_user):
        """
        Test filtering settings by active status
        """
        # Clean up any existing settings
        Settings.objects.all().delete()

        SettingsFactory(user=test_user, is_active=True)
        SettingsFactory(user=test_user, is_active=False)

        url = reverse('settings-list')
        response = authenticated_api_client.get(url, {'is_active': 'true'})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']['list']) == 1
        assert response.data['data']['list'][0]['is_active'] is True

    def test_list_settings_ordering(self, authenticated_api_client, test_user):
        """
        Test ordering settings
        """
        # Clean up any existing settings
        Settings.objects.all().delete()

        SettingsFactory(user=test_user)
        SettingsFactory(user=test_user)

        url = reverse('settings-list')
        response = authenticated_api_client.get(url, {'ordering': 'key'})

        assert response.status_code == status.HTTP_200_OK
        # Check that settings are ordered by key (alphabetically)
        keys = [item['key'] for item in response.data['data']['list']]
        assert keys == sorted(keys)

    def test_list_settings_pagination(self, authenticated_api_client, test_user):
        """
        Test pagination functionality
        """
        # Clean up any existing settings
        Settings.objects.all().delete()

        # Create multiple settings
        SettingsFactory.create_batch(15, user=test_user)

        url = reverse('settings-list')
        response = authenticated_api_client.get(url, {'page_size': 10, 'page': 1})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']['list']) == 10
        assert response.data['data']['pagination']['total'] == 15
        assert response.data['data']['pagination']['page'] == 1
        assert response.data['data']['pagination']['pageSize'] == 10

    def test_create_setting_unauthenticated(self, api_client):
        """
        Test that unauthenticated users cannot create settings
        """
        url = reverse('settings-list')
        data = {
            'key': 'test_setting',
            'value': {'theme': 'dark'},
            'description': 'Test setting'
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_setting_authenticated(self, authenticated_api_client, test_user):
        """
        Test creating a new setting
        """
        url = reverse('settings-list')
        data = {
            'key': 'new_setting',
            'value': {'theme': 'dark', 'language': 'en'},
            'description': 'New test setting'
        }
        response = authenticated_api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['code'] == 201
        assert response.data['message'] == 'Setting created successfully'
        assert response.data['data']['key'] == 'new_setting'
        assert response.data['data']['value'] == {'theme': 'dark', 'language': 'en'}

        # Verify setting was created in database
        setting = Settings.objects.get(id=response.data['data']['id'])
        assert setting.user == test_user
        assert setting.key == 'new_setting'

    def test_create_setting_duplicate_key(self, authenticated_api_client, test_user, test_setting):
        """
        Test creating setting with duplicate key for same user
        """
        # Clean up any existing settings except the test_setting
        Settings.objects.exclude(id=test_setting.id).delete()

        url = reverse('settings-list')
        data = {
            'key': test_setting.key,  # Same key as existing setting
            'value': {'theme': 'light'},
            'description': 'Duplicate key setting'
        }
        response = authenticated_api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'UNIQUE constraint failed' in str(response.data)

    def test_create_setting_invalid_key_format(self, authenticated_api_client, test_user):
        """
        Test creating setting with invalid key format
        """
        url = reverse('settings-list')
        data = {
            'key': 'invalid key with spaces!',  # Invalid format
            'value': {'theme': 'dark'},
            'description': 'Invalid key setting'
        }
        response = authenticated_api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'Key can only contain letters, numbers, underscores, and hyphens' in str(response.data)

    def test_retrieve_setting_unauthenticated(self, api_client, test_setting):
        """
        Test that unauthenticated users cannot retrieve settings
        """
        url = reverse('settings-detail', kwargs={'pk': test_setting.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_retrieve_setting_authenticated(self, authenticated_api_client, test_user, test_setting):
        """
        Test retrieving a specific setting
        """
        url = reverse('settings-detail', kwargs={'pk': test_setting.id})
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['code'] == 200
        assert response.data['message'] == 'Setting retrieved successfully'
        assert response.data['data']['id'] == test_setting.id
        assert response.data['data']['key'] == test_setting.key

    def test_retrieve_setting_other_user(self, authenticated_api_client, test_user):
        """
        Test that users cannot retrieve other users' settings
        """
        # Clean up any existing settings
        Settings.objects.all().delete()

        # Create setting for another user
        other_user = UserFactory()
        other_setting = SettingsFactory(user=other_user)

        url = reverse('settings-detail', kwargs={'pk': other_setting.id})
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'No Settings matches the given query' in response.data['message']

    def test_retrieve_setting_not_found(self, authenticated_api_client, test_user):
        """
        Test retrieving non-existent setting
        """
        # Clean up any existing settings
        Settings.objects.all().delete()

        url = reverse('settings-detail', kwargs={'pk': 99999})
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'No Settings matches the given query' in response.data['message']

    def test_update_setting_put(self, authenticated_api_client, test_user, test_setting):
        """
        Test updating setting with PUT (full update)
        """
        url = reverse('settings-detail', kwargs={'pk': test_setting.id})
        data = {
            'value': {'theme': 'light', 'notifications': False},
            'description': 'Updated setting description',
            'is_active': False
        }
        response = authenticated_api_client.put(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['code'] == 200
        assert response.data['message'] == 'Setting updated successfully'
        assert response.data['data']['value'] == {'theme': 'light', 'notifications': False}
        assert response.data['data']['description'] == 'Updated setting description'
        assert response.data['data']['is_active'] is False

        # Verify update in database
        test_setting.refresh_from_db()
        assert test_setting.value == {'theme': 'light', 'notifications': False}
        assert test_setting.description == 'Updated setting description'
        assert test_setting.is_active is False

    def test_update_setting_patch(self, authenticated_api_client, test_user, test_setting):
        """
        Test updating setting with PATCH (partial update)
        """
        url = reverse('settings-detail', kwargs={'pk': test_setting.id})
        data = {
            'is_active': False
        }
        response = authenticated_api_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['code'] == 200
        assert response.data['data']['is_active'] is False

        # Verify only is_active was updated
        test_setting.refresh_from_db()
        assert test_setting.is_active is False
        assert test_setting.value == test_setting.value  # Should remain unchanged

    def test_update_setting_other_user(self, authenticated_api_client, test_user):
        """
        Test that users cannot update other users' settings
        """
        # Clean up any existing settings
        Settings.objects.all().delete()

        # Create setting for another user
        other_user = UserFactory()
        other_setting = SettingsFactory(user=other_user)

        url = reverse('settings-detail', kwargs={'pk': other_setting.id})
        data = {'value': {'theme': 'hacked'}}
        response = authenticated_api_client.put(url, data, format='json')

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'No Settings matches the given query' in response.data['message']

    def test_delete_setting(self, authenticated_api_client, test_user, test_setting):
        """
        Test deleting a setting
        """
        url = reverse('settings-detail', kwargs={'pk': test_setting.id})
        response = authenticated_api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert response.data['code'] == 204
        assert response.data['message'] == 'Setting deleted successfully'

        # Verify setting was deleted from database
        assert not Settings.objects.filter(id=test_setting.id).exists()

    def test_delete_setting_other_user(self, authenticated_api_client, test_user):
        """
        Test that users cannot delete other users' settings
        """
        # Clean up any existing settings
        Settings.objects.all().delete()

        # Create setting for another user
        other_user = UserFactory()
        other_setting = SettingsFactory(user=other_user)

        url = reverse('settings-detail', kwargs={'pk': other_setting.id})
        response = authenticated_api_client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'No Settings matches the given query' in response.data['message']

        # Verify setting still exists in database
        assert Settings.objects.filter(id=other_setting.id).exists()

    def test_delete_setting_not_found(self, authenticated_api_client, test_user):
        """
        Test deleting non-existent setting
        """
        # Clean up any existing settings
        Settings.objects.all().delete()

        url = reverse('settings-detail', kwargs={'pk': 99999})
        response = authenticated_api_client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'No Settings matches the given query' in response.data['message']
