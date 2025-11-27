"""
Views handling threadline share link lifecycle and public access.
"""

import logging

from django.contrib.auth.hashers import check_password
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .base import BaseAPIView
from ..models import EmailMessage, ThreadlineShareLink
from ..serializers import EmailMessageSerializer
from ..serializers.share_link import (
    ThreadlineShareLinkSerializer,
    ThreadlineShareLinkCreateSerializer,
    SharePasswordSerializer,
)

logger = logging.getLogger(__name__)


class ThreadlineShareLinkAPIView(BaseAPIView):
    """
    Create or refresh share link for a specific email message.
    """

    def post(self, request, uuid):
        """
        Create or refresh share link for the given email message.
        """
        email_message = get_object_or_404(
            EmailMessage,
            uuid=uuid,
            user=request.user
        )

        serializer = ThreadlineShareLinkCreateSerializer(
            data=request.data,
            context={
                'email_message': email_message,
                'owner': request.user
            }
        )
        serializer.is_valid(raise_exception=True)
        share_link = serializer.save()

        data_serializer = ThreadlineShareLinkSerializer(
            share_link,
            context={'request': request}
        )

        return Response({
            'code': 201,
            'message': _('Share link created successfully'),
            'data': {
                'share_link': data_serializer.data,
                'password': getattr(share_link, 'plain_password', '')
            }
        }, status=status.HTTP_201_CREATED)


class ThreadlineShareLinkDetailAPIView(BaseAPIView):
    """
    Retrieve or delete a specific share link (owner only).
    """

    def get_queryset(self):
        """
        Base queryset for share links.
        """
        return ThreadlineShareLink.objects.select_related(
            'email_message',
            'owner'
        )

    def get(self, request, share_uuid):
        """
        Retrieve share link details for owner.
        """
        share_link = get_object_or_404(
            self.get_queryset(),
            uuid=share_uuid,
            owner=request.user
        )
        serializer = ThreadlineShareLinkSerializer(
            share_link,
            context={'request': request}
        )
        return Response({
            'code': 200,
            'message': _('Share link retrieved successfully'),
            'data': serializer.data
        }, status=status.HTTP_200_OK)

    def delete(self, request, share_uuid):
        """
        Deactivate share link owned by current user.
        """
        share_link = get_object_or_404(
            self.get_queryset(),
            uuid=share_uuid,
            owner=request.user
        )
        share_link.deactivate()
        logger.info(
            "Share link %s deactivated by user %s",
            share_uuid,
            request.user.id
        )
        return Response({
            'code': 204,
            'message': _('Share link deactivated successfully'),
            'data': None
        }, status=status.HTTP_204_NO_CONTENT)


class PublicShareLinkAPIView(APIView):
    """
    Public endpoint for accessing shared threadline content.
    """

    permission_classes = [AllowAny]

    def get(self, request, share_uuid):
        """
        Retrieve share metadata or full threadline if no password required.
        """
        share_link = self._get_share_link_or_410(share_uuid)
        if isinstance(share_link, Response):
            return share_link

        serializer = ThreadlineShareLinkSerializer(
            share_link,
            context={'request': request}
        )

        if share_link.password_hash:
            return Response({
                'code': 200,
                'message': _('Password required'),
                'data': {
                    'requires_password': True,
                    'share': serializer.data
                }
            }, status=status.HTTP_200_OK)

        return self._build_share_success_response(
            request,
            share_link,
            serializer.data
        )

    def _build_share_success_response(self, request, share_link, share_data):
        """
        Return serialized email message data for public consumption.
        """
        message_serializer = EmailMessageSerializer(
            share_link.email_message,
            context={'request': request}
        )
        share_link.mark_viewed()
        return Response({
            'code': 200,
            'message': _('Share link retrieved successfully'),
            'data': {
                'requires_password': False,
                'share': share_data,
                'threadline': message_serializer.data
            }
        }, status=status.HTTP_200_OK)

    def _get_share_link_or_410(self, share_uuid):
        """
        Fetch share link ensuring it is active and not expired.
        """
        share_link = get_object_or_404(ThreadlineShareLink, uuid=share_uuid)
        if not share_link.is_active or share_link.is_expired():
            share_link.deactivate()
            return Response({
                'code': 410,
                'message': _('Share link has expired or is inactive'),
                'data': None
            }, status=status.HTTP_410_GONE)
        return share_link


class PublicShareLinkVerifyAPIView(PublicShareLinkAPIView):
    """
    Handle password verification for protected share links.
    """

    def post(self, request, share_uuid):
        """
        Verify password and return threadline content.
        """
        share_link = self._get_share_link_or_410(share_uuid)
        if isinstance(share_link, Response):
            return share_link

        serializer = SharePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not share_link.password_hash:
            return self._build_share_success_response(
                request,
                share_link,
                ThreadlineShareLinkSerializer(
                    share_link,
                    context={'request': request}
                ).data
            )

        password = serializer.validated_data['password']
        if not check_password(password, share_link.password_hash):
            return Response({
                'code': 403,
                'message': _('Invalid password'),
                'data': None
            }, status=status.HTTP_403_FORBIDDEN)

        share_data = ThreadlineShareLinkSerializer(
            share_link,
            context={'request': request}
        ).data
        return self._build_share_success_response(
            request,
            share_link,
            share_data
        )
