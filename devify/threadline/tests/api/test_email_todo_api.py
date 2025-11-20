"""
Tests for EmailTodo API endpoints

This module contains comprehensive tests for the EmailTodo API CRUD operations,
filtering, pagination, statistics, and batch operations.
"""

import pytest
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from threadline.models import EmailTodo, EmailMessage
from ..fixtures.factories import (
    EmailTodoFactory,
    EmailMessageFactory,
    UserFactory
)


@pytest.mark.django_db
@pytest.mark.api
class TestEmailTodoAPI:
    """
    Test cases for EmailTodo API endpoints
    """

    def test_list_todos_unauthenticated(self, api_client):
        """
        Test that unauthenticated users cannot access TODOs
        """
        url = reverse('todos-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_todos_authenticated_empty(
        self, authenticated_api_client, test_user
    ):
        """
        Test listing TODOs when user has no TODOs
        """
        EmailTodo.objects.all().delete()

        url = reverse('todos-list')
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['code'] == 200
        assert response.data['message'] == 'TODOs retrieved successfully'
        assert response.data['data']['list'] == []
        assert response.data['data']['pagination']['total'] == 0

    def test_list_todos_authenticated_with_data(
        self, authenticated_api_client, test_user, test_email_todo
    ):
        """
        Test listing TODOs when user has TODOs
        """
        url = reverse('todos-list')
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['code'] == 200
        assert len(response.data['data']['list']) == 1
        assert (
            response.data['data']['list'][0]['id'] == test_email_todo.id
        )
        assert (
            response.data['data']['list'][0]['content'] ==
            test_email_todo.content
        )

    def test_list_todos_user_isolation(
        self, authenticated_api_client, test_user
    ):
        """
        Test that users can only see their own TODOs
        """
        EmailTodo.objects.all().delete()

        # Create TODO for another user
        other_user = UserFactory()
        other_todo = EmailTodoFactory(user=other_user)

        url = reverse('todos-list')
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']['list']) == 0

    def test_list_todos_filter_completed(
        self, authenticated_api_client, test_user
    ):
        """
        Test filtering TODOs by completion status
        """
        EmailTodo.objects.all().delete()

        EmailTodoFactory(user=test_user, is_completed=True)
        EmailTodoFactory(user=test_user, is_completed=False)

        url = reverse('todos-list')
        response = authenticated_api_client.get(url, {'is_completed': 'true'})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']['list']) == 1
        assert (
            response.data['data']['list'][0]['is_completed'] is True
        )

    def test_list_todos_filter_priority(
        self, authenticated_api_client, test_user
    ):
        """
        Test filtering TODOs by priority
        """
        EmailTodo.objects.all().delete()

        EmailTodoFactory(user=test_user, priority='high')
        EmailTodoFactory(user=test_user, priority='medium')
        EmailTodoFactory(user=test_user, priority='low')

        url = reverse('todos-list')
        response = authenticated_api_client.get(url, {'priority': 'high'})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']['list']) == 1
        assert response.data['data']['list'][0]['priority'] == 'high'

    def test_list_todos_filter_email_message(
        self, authenticated_api_client, test_user
    ):
        """
        Test filtering TODOs by email message ID
        """
        EmailTodo.objects.all().delete()

        email_message = EmailMessageFactory(user=test_user)
        todo1 = EmailTodoFactory(
            user=test_user, email_message=email_message
        )
        todo2 = EmailTodoFactory(user=test_user)

        url = reverse('todos-list')
        response = authenticated_api_client.get(
            url, {'email_message_id': email_message.id}
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']['list']) == 1
        assert response.data['data']['list'][0]['id'] == todo1.id

    def test_list_todos_filter_owner(
        self, authenticated_api_client, test_user
    ):
        """
        Test filtering TODOs by owner
        """
        EmailTodo.objects.all().delete()

        EmailTodoFactory(user=test_user, owner='John Doe')
        EmailTodoFactory(user=test_user, owner='Jane Smith')

        url = reverse('todos-list')
        response = authenticated_api_client.get(url, {'owner': 'John Doe'})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']['list']) == 1
        assert response.data['data']['list'][0]['owner'] == 'John Doe'

    def test_list_todos_filter_deadline_before(
        self, authenticated_api_client, test_user
    ):
        """
        Test filtering TODOs by deadline before date
        """
        EmailTodo.objects.all().delete()

        deadline1 = timezone.now() + timedelta(days=5)
        deadline2 = timezone.now() + timedelta(days=10)

        todo1 = EmailTodoFactory(user=test_user, deadline=deadline1)
        todo2 = EmailTodoFactory(user=test_user, deadline=deadline2)

        url = reverse('todos-list')
        deadline_before = (timezone.now() + timedelta(days=7)).isoformat()
        response = authenticated_api_client.get(
            url, {'deadline_before': deadline_before}
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']['list']) == 1
        assert response.data['data']['list'][0]['id'] == todo1.id

    def test_list_todos_filter_deadline_after(
        self, authenticated_api_client, test_user
    ):
        """
        Test filtering TODOs by deadline after date
        """
        EmailTodo.objects.all().delete()

        deadline1 = timezone.now() + timedelta(days=5)
        deadline2 = timezone.now() + timedelta(days=10)

        todo1 = EmailTodoFactory(user=test_user, deadline=deadline1)
        todo2 = EmailTodoFactory(user=test_user, deadline=deadline2)

        url = reverse('todos-list')
        deadline_after = (timezone.now() + timedelta(days=7)).isoformat()
        response = authenticated_api_client.get(
            url, {'deadline_after': deadline_after}
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']['list']) == 1
        assert response.data['data']['list'][0]['id'] == todo2.id

    def test_list_todos_search(
        self, authenticated_api_client, test_user
    ):
        """
        Test search functionality in TODOs list
        """
        EmailTodo.objects.all().delete()

        EmailTodoFactory(user=test_user, content='Important meeting TODO')
        EmailTodoFactory(user=test_user, content='Follow up with client')

        url = reverse('todos-list')
        response = authenticated_api_client.get(url, {'search': 'meeting'})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']['list']) == 1
        assert 'meeting' in (
            response.data['data']['list'][0]['content'].lower()
        )

    def test_list_todos_ordering(
        self, authenticated_api_client, test_user
    ):
        """
        Test ordering TODOs
        """
        EmailTodo.objects.all().delete()

        todo1 = EmailTodoFactory(user=test_user, priority='high')
        todo2 = EmailTodoFactory(user=test_user, priority='low')

        url = reverse('todos-list')
        response = authenticated_api_client.get(url, {'ordering': 'priority'})

        assert response.status_code == status.HTTP_200_OK
        priorities = [
            item['priority'] for item in response.data['data']['list']
        ]
        assert priorities == sorted(priorities)

    def test_list_todos_pagination(
        self, authenticated_api_client, test_user
    ):
        """
        Test pagination functionality
        """
        EmailTodo.objects.all().delete()

        EmailTodoFactory.create_batch(15, user=test_user)

        url = reverse('todos-list')
        response = authenticated_api_client.get(
            url, {'page_size': 10, 'page': 1}
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']['list']) == 10
        assert response.data['data']['pagination']['total'] == 15
        assert response.data['data']['pagination']['page'] == 1
        assert response.data['data']['pagination']['pageSize'] == 10

    def test_create_todo_unauthenticated(self, api_client):
        """
        Test that unauthenticated users cannot create TODOs
        """
        url = reverse('todos-list')
        data = {
            'content': 'Test TODO',
            'priority': 'high'
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_todo_authenticated(
        self, authenticated_api_client, test_user
    ):
        """
        Test creating a new TODO
        """
        url = reverse('todos-list')
        data = {
            'content': 'New TODO item',
            'priority': 'medium',
            'owner': 'Test Owner',
            'location': 'Test Location'
        }
        response = authenticated_api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['code'] == 201
        assert response.data['message'] == 'TODO created successfully'
        assert response.data['data']['content'] == 'New TODO item'
        assert response.data['data']['priority'] == 'medium'

        # Verify TODO was created in database
        todo = EmailTodo.objects.get(id=response.data['data']['id'])
        assert todo.user == test_user
        assert todo.content == 'New TODO item'

    def test_create_todo_with_email_message(
        self, authenticated_api_client, test_user, test_email_message
    ):
        """
        Test creating TODO with email message
        """
        url = reverse('todos-list')
        data = {
            'content': 'TODO from email',
            'email_message_id': test_email_message.id,
            'priority': 'high'
        }
        response = authenticated_api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert (
            response.data['data']['email_message']['id'] ==
            test_email_message.id
        )

    def test_create_todo_invalid_priority(
        self, authenticated_api_client, test_user
    ):
        """
        Test creating TODO with invalid priority
        """
        url = reverse('todos-list')
        data = {
            'content': 'Test TODO',
            'priority': 'invalid_priority'
        }
        response = authenticated_api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_retrieve_todo_unauthenticated(self, api_client, test_email_todo):
        """
        Test that unauthenticated users cannot retrieve TODOs
        """
        url = reverse('todos-detail', kwargs={'pk': test_email_todo.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_retrieve_todo_authenticated(
        self, authenticated_api_client, test_user, test_email_todo
    ):
        """
        Test retrieving a specific TODO
        """
        url = reverse('todos-detail', kwargs={'pk': test_email_todo.id})
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['code'] == 200
        assert response.data['message'] == 'TODO retrieved successfully'
        assert response.data['data']['id'] == test_email_todo.id
        assert response.data['data']['content'] == test_email_todo.content

    def test_retrieve_todo_other_user(
        self, authenticated_api_client, test_user
    ):
        """
        Test that users cannot retrieve other users' TODOs
        """
        EmailTodo.objects.all().delete()

        # Create TODO for another user
        other_user = UserFactory()
        other_todo = EmailTodoFactory(user=other_user)

        url = reverse('todos-detail', kwargs={'pk': other_todo.id})
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_todo_not_found(
        self, authenticated_api_client, test_user
    ):
        """
        Test retrieving non-existent TODO
        """
        EmailTodo.objects.all().delete()

        url = reverse('todos-detail', kwargs={'pk': 99999})
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_todo_patch(
        self, authenticated_api_client, test_user, test_email_todo
    ):
        """
        Test updating TODO with PATCH (partial update)
        """
        url = reverse('todos-detail', kwargs={'pk': test_email_todo.id})
        data = {
            'is_completed': True,
            'priority': 'high'
        }
        response = authenticated_api_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['code'] == 200
        assert response.data['message'] == 'TODO updated successfully'
        assert response.data['data']['is_completed'] is True
        assert response.data['data']['priority'] == 'high'

        # Verify update in database
        test_email_todo.refresh_from_db()
        assert test_email_todo.is_completed is True
        assert test_email_todo.priority == 'high'

    def test_update_todo_mark_completed(
        self, authenticated_api_client, test_user, test_email_todo
    ):
        """
        Test marking TODO as completed
        """
        assert test_email_todo.is_completed is False
        assert test_email_todo.completed_at is None

        url = reverse('todos-detail', kwargs={'pk': test_email_todo.id})
        data = {'is_completed': True}
        response = authenticated_api_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        test_email_todo.refresh_from_db()
        assert test_email_todo.is_completed is True
        assert test_email_todo.completed_at is not None

    def test_update_todo_other_user(
        self, authenticated_api_client, test_user
    ):
        """
        Test that users cannot update other users' TODOs
        """
        EmailTodo.objects.all().delete()

        # Create TODO for another user
        other_user = UserFactory()
        other_todo = EmailTodoFactory(user=other_user)

        url = reverse('todos-detail', kwargs={'pk': other_todo.id})
        data = {'is_completed': True}
        response = authenticated_api_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_todo(
        self, authenticated_api_client, test_user, test_email_todo
    ):
        """
        Test deleting a TODO
        """
        todo_id = test_email_todo.id
        url = reverse('todos-detail', kwargs={'pk': todo_id})
        response = authenticated_api_client.delete(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['code'] == 200
        assert response.data['message'] == 'TODO deleted successfully'

        # Verify TODO was deleted from database
        assert not EmailTodo.objects.filter(id=todo_id).exists()

    def test_delete_todo_other_user(
        self, authenticated_api_client, test_user
    ):
        """
        Test that users cannot delete other users' TODOs
        """
        EmailTodo.objects.all().delete()

        # Create TODO for another user
        other_user = UserFactory()
        other_todo = EmailTodoFactory(user=other_user)

        url = reverse('todos-detail', kwargs={'pk': other_todo.id})
        response = authenticated_api_client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Verify TODO still exists in database
        assert EmailTodo.objects.filter(id=other_todo.id).exists()

    def test_delete_todo_not_found(
        self, authenticated_api_client, test_user
    ):
        """
        Test deleting non-existent TODO
        """
        EmailTodo.objects.all().delete()

        url = reverse('todos-detail', kwargs={'pk': 99999})
        response = authenticated_api_client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
@pytest.mark.api
class TestEmailTodoStatsAPI:
    """
    Test cases for EmailTodo statistics API
    """

    def test_stats_unauthenticated(self, api_client):
        """
        Test that unauthenticated users cannot access statistics
        """
        url = reverse('todos-stats')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_stats_authenticated_empty(
        self, authenticated_api_client, test_user
    ):
        """
        Test statistics when user has no TODOs
        """
        EmailTodo.objects.all().delete()

        url = reverse('todos-stats')
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['code'] == 200
        assert response.data['data']['total'] == 0
        assert response.data['data']['completed'] == 0
        assert response.data['data']['incomplete'] == 0
        assert response.data['data']['completion_rate'] == 0.0

    def test_stats_authenticated_with_data(
        self, authenticated_api_client, test_user
    ):
        """
        Test statistics with TODOs
        """
        EmailTodo.objects.all().delete()

        # Create TODOs with different statuses and priorities
        EmailTodoFactory(user=test_user, is_completed=True, priority='high')
        EmailTodoFactory(user=test_user, is_completed=True, priority='medium')
        EmailTodoFactory(user=test_user, is_completed=False, priority='low')
        EmailTodoFactory(user=test_user, is_completed=False, priority='high')

        url = reverse('todos-stats')
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['total'] == 4
        assert response.data['data']['completed'] == 2
        assert response.data['data']['incomplete'] == 2
        assert response.data['data']['completion_rate'] == 50.0
        assert (
            response.data['data']['by_priority']['high'] == 2
        )
        assert (
            response.data['data']['by_priority']['medium'] == 1
        )
        assert response.data['data']['by_priority']['low'] == 1

    def test_stats_user_isolation(
        self, authenticated_api_client, test_user
    ):
        """
        Test that statistics only include user's own TODOs
        """
        EmailTodo.objects.all().delete()

        # Create TODOs for test_user
        EmailTodoFactory(user=test_user, is_completed=True)
        EmailTodoFactory(user=test_user, is_completed=False)

        # Create TODOs for another user
        other_user = UserFactory()
        EmailTodoFactory(user=other_user, is_completed=True)

        url = reverse('todos-stats')
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['total'] == 2


@pytest.mark.django_db
@pytest.mark.api
class TestEmailTodoBatchAPI:
    """
    Test cases for EmailTodo batch operations API
    """

    def test_batch_complete_unauthenticated(self, api_client):
        """
        Test that unauthenticated users cannot batch complete TODOs
        """
        url = reverse('todos-batch')
        data = {'todo_ids': [1, 2, 3]}
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_batch_complete_empty_ids(
        self, authenticated_api_client, test_user
    ):
        """
        Test batch complete with empty todo_ids
        """
        url = reverse('todos-batch')
        data = {'todo_ids': []}
        response = authenticated_api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['code'] == 400
        assert 'todo_ids is required' in response.data['message']

    def test_batch_complete_missing_ids(
        self, authenticated_api_client, test_user
    ):
        """
        Test batch complete without todo_ids
        """
        url = reverse('todos-batch')
        data = {}
        response = authenticated_api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_batch_complete_success(
        self, authenticated_api_client, test_user
    ):
        """
        Test batch completing TODOs
        """
        EmailTodo.objects.all().delete()

        todo1 = EmailTodoFactory(user=test_user, is_completed=False)
        todo2 = EmailTodoFactory(user=test_user, is_completed=False)
        todo3 = EmailTodoFactory(user=test_user, is_completed=True)

        url = reverse('todos-batch')
        data = {'todo_ids': [todo1.id, todo2.id, todo3.id]}
        response = authenticated_api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['code'] == 200
        assert response.data['data']['completed_count'] == 2

        # Verify TODOs were marked as completed
        todo1.refresh_from_db()
        todo2.refresh_from_db()
        assert todo1.is_completed is True
        assert todo2.is_completed is True
        # todo3 was already completed, should remain completed
        todo3.refresh_from_db()
        assert todo3.is_completed is True

    def test_batch_complete_user_isolation(
        self, authenticated_api_client, test_user
    ):
        """
        Test that batch complete only affects user's own TODOs
        """
        EmailTodo.objects.all().delete()

        # Create TODOs for test_user
        todo1 = EmailTodoFactory(user=test_user, is_completed=False)
        todo2 = EmailTodoFactory(user=test_user, is_completed=False)

        # Create TODO for another user
        other_user = UserFactory()
        other_todo = EmailTodoFactory(user=other_user, is_completed=False)

        url = reverse('todos-batch')
        data = {'todo_ids': [todo1.id, todo2.id, other_todo.id]}
        response = authenticated_api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        # Only 2 TODOs should be completed (user's own)
        assert response.data['data']['completed_count'] == 2

        # Verify only user's TODOs were completed
        todo1.refresh_from_db()
        todo2.refresh_from_db()
        other_todo.refresh_from_db()
        assert todo1.is_completed is True
        assert todo2.is_completed is True
        # Other user's TODO should not be completed
        assert other_todo.is_completed is False
