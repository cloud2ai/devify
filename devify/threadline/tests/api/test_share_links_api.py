"""
Tests for Threadline share link API endpoints.
"""

import pytest
from django.urls import reverse
from rest_framework import status

from threadline.models import ThreadlineShareLink
from ..fixtures.factories import ThreadlineShareLinkFactory


@pytest.mark.django_db
@pytest.mark.api
class TestShareLinksAPI:
    """
    Test cases covering share link lifecycle and public access.
    """

    def test_create_share_link_generates_password(
        self,
        authenticated_api_client,
        test_email_message
    ):
        url = reverse('threadlines-share-link', args=[test_email_message.uuid])
        response = authenticated_api_client.post(
            url,
            {'expiration': '7d'},
            format='json'
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.data['data']
        assert data['password']
        assert len(data['password']) == 6
        assert data['password'].isdigit()

        share_link = ThreadlineShareLink.objects.get(
            email_message=test_email_message,
            is_active=True
        )
        assert str(share_link.uuid) == data['share_link']['token']

    def test_share_status_in_list_and_detail(
        self,
        authenticated_api_client,
        test_email_message
    ):
        url = reverse('threadlines-share-link', args=[test_email_message.uuid])
        authenticated_api_client.post(url, {'expiration': '7d'}, format='json')

        list_response = authenticated_api_client.get(
            reverse('threadlines-list'),
            {'search': test_email_message.sender}
        )
        assert list_response.status_code == status.HTTP_200_OK
        items = list_response.data['data']['list']
        target = next(
            (
                item for item in items
                if item['uuid'] == str(test_email_message.uuid)
            ),
            None
        )
        assert target is not None
        share_status = target['share_status']
        assert share_status is not None
        assert 'share_url' in share_status

        detail_response = authenticated_api_client.get(
            reverse('threadlines-detail', args=[test_email_message.uuid])
        )
        assert detail_response.status_code == status.HTTP_200_OK
        detail_share_status = detail_response.data['data']['share_status']
        assert detail_share_status['token'] == share_status['token']

    def test_delete_share_link(self, authenticated_api_client, test_user):
        share_link = ThreadlineShareLinkFactory(
            email_message__user=test_user
        )
        url = reverse('share-links-detail', args=[share_link.uuid])

        response = authenticated_api_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT

        share_link.refresh_from_db()
        assert share_link.is_active is False

    def test_public_share_without_password(
        self,
        api_client,
        test_user
    ):
        share_link = ThreadlineShareLinkFactory(
            email_message__user=test_user,
            password_hash=''
        )
        url = reverse('public-share', args=[share_link.uuid])
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['requires_password'] is False
        assert response.data['data']['threadline']['id'] == (
            share_link.email_message.id
        )

    def test_public_share_password_flow(self, api_client, test_user):
        share_link = ThreadlineShareLinkFactory(email_message__user=test_user)

        meta_response = api_client.get(
            reverse('public-share', args=[share_link.uuid])
        )
        assert meta_response.status_code == status.HTTP_200_OK
        assert meta_response.data['data']['requires_password'] is True

        verify_url = reverse('public-share-verify', args=[share_link.uuid])
        failed = api_client.post(
            verify_url,
            {'password': '000000'},
            format='json'
        )
        assert failed.status_code == status.HTTP_403_FORBIDDEN

        success = api_client.post(
            verify_url,
            {'password': '123456'},
            format='json'
        )
        assert success.status_code == status.HTTP_200_OK
        assert success.data['data']['threadline']['id'] == (
            share_link.email_message.id
        )
