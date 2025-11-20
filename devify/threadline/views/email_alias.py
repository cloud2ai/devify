"""
EmailAlias Management API Views

This module provides API endpoints for managing email aliases in auto-assign
mode, including CRUD operations, validation, and user data isolation.
"""

import logging
from typing import Dict, Any

from django.http import Http404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from threadline.models import EmailAlias
from ..serializers import (
    EmailAliasSerializer,
    EmailAliasCreateSerializer
)
from .base import BaseAPIView

logger = logging.getLogger(__name__)


class EmailAliasAPIView(BaseAPIView):
    """
    Email Alias management API

    Provides CRUD operations for user email aliases with proper user
    data isolation and validation.
    """

    def get_queryset(self):
        """Get user's email aliases"""
        return EmailAlias.objects.filter(
            user=self.request.user
        ).order_by('-created_at')

    @extend_schema(
        summary="List user's email aliases",
        description="Get all email aliases for the authenticated user",
        responses={
            200: EmailAliasSerializer(many=True),
            401: "Authentication required"
        }
    )
    def get(self, request) -> Response:
        """List all email aliases for authenticated user"""
        try:
            aliases = self.get_queryset()
            serializer = EmailAliasSerializer(aliases, many=True)

            logger.info(
                f"Retrieved {len(aliases)} email aliases "
                f"for user {request.user.username}"
            )

            return Response({
                'success': True,
                'data': serializer.data,
                'count': len(aliases)
            })

        except Exception as e:
            logger.error(f"Error retrieving email aliases: {e}")
            return Response({
                'success': False,
                'error': 'Failed to retrieve email aliases'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        summary="Create new email alias",
        description="Create a new email alias for the authenticated user",
        request=EmailAliasCreateSerializer,
        responses={
            201: EmailAliasSerializer,
            400: "Validation error",
            401: "Authentication required",
            409: "Alias already exists"
        }
    )
    def post(self, request) -> Response:
        """Create new email alias"""
        try:
            serializer = EmailAliasCreateSerializer(data=request.data)

            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            # Check alias uniqueness
            alias = serializer.validated_data['alias']
            if not EmailAlias.is_unique(alias):
                return Response({
                    'success': False,
                    'error': f'Alias "{alias}" already exists'
                }, status=status.HTTP_409_CONFLICT)

            # Create alias for authenticated user
            email_alias = serializer.save(user=request.user)

            response_serializer = EmailAliasSerializer(email_alias)

            logger.info(
                f"Created email alias {email_alias.full_email_address()} "
                f"for user {request.user.username}"
            )

            return Response({
                'success': True,
                'data': response_serializer.data,
                'message': f'Email alias "{alias}" created successfully'
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error creating email alias: {e}")
            return Response({
                'success': False,
                'error': 'Failed to create email alias'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EmailAliasDetailAPIView(BaseAPIView):
    """
    Email Alias detail API

    Provides operations for individual email aliases including
    retrieval, update, and deletion.
    """

    def get_object(self, alias_id: int):
        """Get email alias object with user ownership validation"""
        try:
            return EmailAlias.objects.get(
                id=alias_id,
                user=self.request.user
            )
        except EmailAlias.DoesNotExist:
            raise Http404("Email alias not found")

    @extend_schema(
        summary="Get email alias details",
        description="Retrieve details of a specific email alias",
        responses={
            200: EmailAliasSerializer,
            401: "Authentication required",
            404: "Alias not found"
        }
    )
    def get(self, request, alias_id: int) -> Response:
        """Get specific email alias details"""
        try:
            alias = self.get_object(alias_id)
            serializer = EmailAliasSerializer(alias)

            return Response({
                'success': True,
                'data': serializer.data
            })

        except Http404:
            return Response({
                'success': False,
                'error': 'Email alias not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error retrieving email alias {alias_id}: {e}")
            return Response({
                'success': False,
                'error': 'Failed to retrieve email alias'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        summary="Update email alias",
        description="Update an existing email alias",
        request=EmailAliasCreateSerializer,
        responses={
            200: EmailAliasSerializer,
            400: "Validation error",
            401: "Authentication required",
            404: "Alias not found",
            409: "Alias already exists"
        }
    )
    def put(self, request, alias_id: int) -> Response:
        """Update email alias"""
        try:
            alias = self.get_object(alias_id)
            serializer = EmailAliasCreateSerializer(
                alias, data=request.data, partial=False
            )

            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            # Check uniqueness if alias changed
            new_alias = serializer.validated_data['alias']
            if (new_alias != alias.alias and
                not EmailAlias.is_unique(new_alias)):
                return Response({
                    'success': False,
                    'error': f'Alias "{new_alias}" already exists'
                }, status=status.HTTP_409_CONFLICT)

            updated_alias = serializer.save()
            response_serializer = EmailAliasSerializer(updated_alias)

            logger.info(
                f"Updated email alias {updated_alias.full_email_address()} "
                f"for user {request.user.username}"
            )

            return Response({
                'success': True,
                'data': response_serializer.data,
                'message': 'Email alias updated successfully'
            })

        except Http404:
            return Response({
                'success': False,
                'error': 'Email alias not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error updating email alias {alias_id}: {e}")
            return Response({
                'success': False,
                'error': 'Failed to update email alias'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        summary="Delete email alias",
        description="Delete an existing email alias",
        responses={
            200: "Alias deleted successfully",
            401: "Authentication required",
            404: "Alias not found"
        }
    )
    def delete(self, request, alias_id: int) -> Response:
        """Delete email alias"""
        try:
            alias = self.get_object(alias_id)
            alias_email = alias.full_email_address()
            alias.delete()

            logger.info(
                f"Deleted email alias {alias_email} "
                f"for user {request.user.username}"
            )

            return Response({
                'success': True,
                'message': f'Email alias "{alias.alias}" deleted successfully'
            })

        except Http404:
            return Response({
                'success': False,
                'error': 'Email alias not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error deleting email alias {alias_id}: {e}")
            return Response({
                'success': False,
                'error': 'Failed to delete email alias'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EmailAliasValidationAPIView(BaseAPIView):
    """
    Email Alias validation API

    Provides validation endpoints for checking alias availability
    and format validation.
    """

    @extend_schema(
        summary="Validate email alias availability",
        description="Check if an email alias is available for use",
        parameters=[
            OpenApiParameter(
                name='alias',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Alias to validate',
                required=True
            )
        ],
        responses={
            200: "Validation result",
            400: "Missing alias parameter",
            401: "Authentication required"
        }
    )
    def get(self, request) -> Response:
        """Validate alias availability"""
        try:
            alias = request.query_params.get('alias')

            if not alias:
                return Response({
                    'success': False,
                    'error': 'Alias parameter is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Validate alias format (basic validation)
            if not self._is_valid_alias_format(alias):
                return Response({
                    'success': False,
                    'available': False,
                    'error': 'Invalid alias format'
                })

            # Check uniqueness
            is_available = EmailAlias.is_unique(alias)

            return Response({
                'success': True,
                'alias': alias,
                'available': is_available,
                'message': (
                    'Alias is available' if is_available
                    else 'Alias already exists'
                )
            })

        except Exception as e:
            logger.error(f"Error validating alias: {e}")
            return Response({
                'success': False,
                'error': 'Failed to validate alias'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _is_valid_alias_format(self, alias: str) -> bool:
        """
        Validate alias format

        Args:
            alias: Alias string to validate

        Returns:
            Whether the alias format is valid
        """
        import re

        # Basic email local part validation
        # Allow alphanumeric, dots, hyphens, underscores
        pattern = r'^[a-zA-Z0-9._-]+$'

        if not re.match(pattern, alias):
            return False

        # Check length constraints
        if len(alias) < 1 or len(alias) > 64:
            return False

        # Ensure doesn't start or end with special characters
        if alias.startswith('.') or alias.endswith('.'):
            return False

        # Check reserved words
        reserved_words = [
            'admin', 'administrator', 'root', 'postmaster',
            'webmaster', 'hostmaster', 'noreply', 'no-reply'
        ]

        if alias.lower() in reserved_words:
            return False

        return True
